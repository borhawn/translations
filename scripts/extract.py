#!/usr/bin/env python3
"""Step 2 — turn the 119 English pages into translation work units.

Writes work/pages.json (one record per English page: every translatable string,
with the markup held back) and work/units.jsonl (the de-duplicated strings that
actually get sent to a translator).

Usage: python3 scripts/extract.py <export.csv> [--out work]
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wpml import export as E, markup as M, phpserial as PS

# Plain single-value columns that are translated as-is.
PLAIN_FIELDS = {
    "title": E.TITLE,
    "excerpt": E.EXCERPT,
    "subtitle": E.SUBTITLE,
    "seo_title": E.SEO_TITLE,
    "seo_description": E.SEO_DESC,
    "og_title": E.OG_TITLE,
    "og_description": E.OG_DESC,
    "focus_keyword": E.FOCUS_KEYWORD,
    "acf_address": E.ACF_ADDRESS,
    "acf_city1": E.ACF_CITY1,
    "acf_city2": E.ACF_CITY2,
    "acf_cities": E.ACF_CITIES,
}

# Pipe-delimited taxonomy columns.
TERM_FIELDS = {"categories": E.CATEGORIES, "tags": E.TAGS, "relation_tags": E.RELATION_TAGS}

# Media metadata columns, also pipe-delimited, one entry per attachment.
MEDIA_FIELDS = {"media_title": E.MEDIA_TITLE, "media_caption": E.MEDIA_CAPTION,
                "media_description": E.MEDIA_DESC, "media_alt": E.MEDIA_ALT}

# Serialized blobs: column -> the keys whose string values are translatable.
SERIAL_FIELDS = {
    E.SCHEMA_SERVICE: {"name", "description", "serviceType"},
    E.FEEDBACK_ATTS[0]: {"subject", "submit_button_text",
                         "customThankyouHeading", "customThankyouMessage"},
    E.FEEDBACK_ATTS[1]: {"subject", "submit_button_text",
                         "customThankyouHeading", "customThankyouMessage"},
    E.FEEDBACK_ATTS[2]: {"subject", "submit_button_text",
                         "customThankyouHeading", "customThankyouMessage"},
}


def extract_page(row):
    page = {
        "id": row[E.ID],
        "group": row[E.GROUP],
        "title": row[E.TITLE],
        "slug": row[E.SLUG],
        "status": row[E.STATUS],
        "parent": row[E.PARENT],
        "fields": {},        # name -> source string
        "terms": {},         # name -> [term, ...]
        "segments": {},      # uid  -> source text from the body
        "serial": {},        # column index -> {key: source string}
    }
    for name, col in PLAIN_FIELDS.items():
        if row[col].strip():
            page["fields"][name] = row[col]
    for name, col in MEDIA_FIELDS.items():
        if row[col].strip("| "):
            page["terms"][name] = row[col].split("|")
    for name, col in TERM_FIELDS.items():
        if row[col].strip():
            page["terms"][name] = [t for t in row[col].split("|") if t]
    page["segments"] = M.translatable(M.tokenize(row[E.CONTENT]))
    for col, keys in SERIAL_FIELDS.items():
        if row[col].strip():
            data = PS.loads(row[col])
            found = {k: v for k, v in data.items() if k in keys and isinstance(v, str)}
            if found:
                page["serial"][str(col)] = found
    return page


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--out", default="work")
    ap.add_argument("--seo", default="seo/en.json",
                    help="reviewed English SEO baseline; its strings replace the "
                         "CSV's for extraction, so what gets translated is what "
                         "assemble.py will actually write")
    args = ap.parse_args()

    ex = E.load(args.csv)

    seo = {}
    if os.path.exists(args.seo):
        with open(args.seo, encoding="utf-8") as fh:
            seo = json.load(fh)["pages"]
    for row in ex.english:
        entry = seo.get(row[E.ID])
        if not entry:
            continue
        if entry.get("title"):
            row[E.SEO_TITLE] = entry["title"]
        if entry.get("description"):
            row[E.SEO_DESC] = entry["description"]
        if entry.get("focus_keyword"):
            row[E.FOCUS_KEYWORD] = entry["focus_keyword"]
        # Open Graph falls back to the SEO pair, so it needs the same strings.
        if not row[E.OG_TITLE].strip():
            row[E.OG_TITLE] = row[E.SEO_TITLE]
        if not row[E.OG_DESC].strip():
            row[E.OG_DESC] = row[E.SEO_DESC]
    os.makedirs(args.out, exist_ok=True)

    pages = [extract_page(r) for r in ex.english]
    with open(os.path.join(args.out, "pages.json"), "w", encoding="utf-8") as fh:
        json.dump(pages, fh, ensure_ascii=False, indent=1)

    # De-duplicated units. `kind` steers the prompt: a body sentence, a short
    # UI label and an SEO title all need different instructions.
    units = {}
    def add(kind, text, page_id):
        text = text.strip()
        if not text or not M.HAS_WORD_RE.search(text) or M.is_placeholder(text):
            return
        uid = M.segment_id(text)
        unit = units.setdefault(uid, {"uid": uid, "kind": kind, "text": text, "pages": []})
        if page_id not in unit["pages"]:
            unit["pages"].append(page_id)

    for page in pages:
        for name, value in page["fields"].items():
            add(name if name.startswith(("seo", "og", "focus")) else "field", value, page["id"])
        for name, values in page["terms"].items():
            for value in values:
                add("media" if name.startswith("media") else "term", value, page["id"])
        for text in page["segments"].values():
            add("body", text, page["id"])
        for entries in page["serial"].values():
            for value in entries.values():
                add("field", value, page["id"])

    with open(os.path.join(args.out, "units.jsonl"), "w", encoding="utf-8") as fh:
        for unit in units.values():
            fh.write(json.dumps(unit, ensure_ascii=False) + "\n")

    by_kind = {}
    for unit in units.values():
        by_kind[unit["kind"]] = by_kind.get(unit["kind"], 0) + 1
    print(f"pages            {len(pages)}")
    print(f"unique units     {len(units)}")
    for kind, count in sorted(by_kind.items(), key=lambda kv: -kv[1]):
        print(f"  {kind:16} {count}")
    print(f"chars to translate per language {sum(len(u['text']) for u in units.values()):,}")


if __name__ == "__main__":
    main()
