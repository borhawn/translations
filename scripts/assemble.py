#!/usr/bin/env python3
"""Steps 8-9 — build the import CSV.

Original 161 rows are copied byte-for-byte; the new rows are appended.

    python3 scripts/assemble.py export.csv --work work --out import.csv
    python3 scripts/assemble.py export.csv --work work --out de.csv --langs de
"""

import argparse
import datetime
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wpml import export as E, langs, markup as M, phpserial as PS, slugs
from extract import MEDIA_FIELDS, PLAIN_FIELDS, SERIAL_FIELDS, TERM_FIELDS

# --- the rule table from docs/analysis.md, as code -------------------------

BLANK_COLUMNS = (E.ID, E.PERMALINK, E.ANALYTIC_ID, E.CANONICAL,
                 E.JETPACK_CACHE, E.ALP_PROCESSED, E.LANG_DUPLICATE_OF)

CONSTANTS = {
    E.IMPORT_SRC_LANG: "en",
    E.IMPORT_SRC_LANG_2: "en",
    E.PRIORITIES: "Optional",
    E.LAST_EDIT_MODE: "native-editor",
}

# Parent is resolved by the second import pass, not here.
DEFERRED = (E.PARENT, E.PARENT_SLUG)


def build_row(source, code, translations, seo, now):
    """One translation row, derived from its English source row."""
    row = list(source)

    for col in BLANK_COLUMNS:
        row[col] = ""
    for col, value in CONSTANTS.items():
        row[col] = value
    for col in DEFERRED:
        row[col] = ""

    row[E.LANG] = row[E.IMPORT_LANG] = row[E.IMPORT_LANG_2] = code
    row[E.WPML_TRANSLATION_ID] = source[E.ID]
    row[E.GROUP] = row[E.GROUP_2] = source[E.GROUP] or source[E.ID]
    row[E.IMPORT_KEY] = f"{source[E.ID]}-{code}"
    row[E.MODIFIED] = now

    def tr(text):
        """Translated form of a source string, English if it is missing."""
        if not text.strip():
            return text
        return translations.get(M.segment_id(text.strip()), text)

    # Body: English tokens, translated text. Markup cannot change.
    tokens = M.tokenize(source[E.CONTENT])
    row[E.CONTENT] = M.rebuild(
        tokens, {uid: tr(text) for uid, text in M.translatable(tokens).items()})
    row[E.WORD_COUNT] = str(M.plain_words(row[E.CONTENT]))

    # SEO: English baseline from seo/en.json, then its translation.
    entry = seo.get(source[E.ID], {})
    for col, key in ((E.SEO_TITLE, "title"), (E.SEO_DESC, "description"),
                     (E.FOCUS_KEYWORD, "focus_keyword")):
        english = entry.get(key) or (source[col] if key != "focus_keyword" else "")
        row[col] = tr(english) if english else ""
    # Open Graph falls back to the SEO pair when the English row has none, and
    # also when the site's own OG string overflows its budget (several do).
    for col, seo_col, limit in ((E.OG_TITLE, E.SEO_TITLE, 60),
                                (E.OG_DESC, E.SEO_DESC, 155)):
        candidate = tr(source[col]) if source[col].strip() else row[seo_col]
        if len(html.unescape(candidate)) > limit:
            candidate = row[seo_col]
        row[col] = candidate

    for name, col in PLAIN_FIELDS.items():
        if name in ("seo_title", "seo_description", "og_title",
                    "og_description", "focus_keyword"):
            continue
        row[col] = tr(source[col])

    for col in list(TERM_FIELDS.values()) + list(MEDIA_FIELDS.values()):
        if source[col].strip("| "):
            row[col] = "|".join(tr(part) for part in source[col].split("|"))

    for col, keys in SERIAL_FIELDS.items():
        if source[col].strip():
            row[col] = PS.translate_in_place(
                source[col], keys,
                lambda v: v if M.is_placeholder(v) else tr(v))

    # Feedback form definitions: only the label= attributes are copy.
    for col in E.FEEDBACK_FORMS:
        if source[col].strip():
            row[col] = _translate_labels(source[col], tr)

    row[E.TITLE] = tr(source[E.TITLE])
    return row


def _translate_labels(shortcode_text, tr):
    import re
    return re.sub(r"(label=)(['\"])(.*?)\2",
                  lambda m: f"{m.group(1)}{m.group(2)}{tr(m.group(3))}{m.group(2)}",
                  shortcode_text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--work", default="work")
    ap.add_argument("--seo", default="seo/en.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--langs", default="all")
    args = ap.parse_args()

    ex = E.load(args.csv)
    codes = langs.CODES if args.langs == "all" else args.langs.split(",")
    existing = ex.existing_pairs()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    seo = {}
    if os.path.exists(args.seo):
        with open(args.seo, encoding="utf-8") as fh:
            seo = json.load(fh)["pages"]

    new_rows, skipped = [], 0
    for code in codes:
        path = os.path.join(args.work, "translations", f"{code}.json")
        if not os.path.exists(path):
            print(f"{code}: no translations, skipped", file=sys.stderr)
            continue
        with open(path, encoding="utf-8") as fh:
            translations = json.load(fh)
        taken = {r[E.SLUG] for r in ex.rows if r[E.LANG] == code and r[E.SLUG]}
        for source in sorted(ex.english, key=lambda r: int(r[E.ID])):
            group = source[E.GROUP] or source[E.ID]
            if (group, code) in existing:
                skipped += 1
                continue
            row = build_row(source, code, translations, seo, now)
            row[E.SLUG] = slugs.unique_slug(slugs.sanitize_title(row[E.TITLE]), taken)
            new_rows.append(row)

    E.write(args.out, ex.raw_lines["header"], ex.raw_lines["records"], new_rows)
    print(f"original rows {len(ex.rows)}  new rows {len(new_rows)}  "
          f"skipped (already translated) {skipped}")
    print(f"total {len(ex.rows) + len(new_rows)} -> {args.out}")


if __name__ == "__main__":
    main()
