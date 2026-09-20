#!/usr/bin/env python3
"""Inventory the WPML page export before generating translations.

Usage: python3 scripts/analyze_export.py <export.csv>
"""
import collections
import csv
import hashlib
import re
import sys

csv.field_size_limit(10 ** 9)

COL_ID, COL_TITLE, COL_CONTENT = 0, 1, 2
COL_LANG, COL_SRC_LANG, COL_GROUP = 8, 10, 11
COL_CATS, COL_TAGS, COL_RELTAGS = 19, 20, 22
COL_SUBTITLE = 31
COL_IMPORT_KEY, COL_STATUS, COL_SLUG, COL_PARENT = 86, 92, 98, 101

SHORTCODE_RE = re.compile(r"\[/?[^\]]+\]")
HTML_RE = re.compile(r"<[^>]*>")


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        return next(reader), list(reader)


def plain_text(content):
    text = SHORTCODE_RE.sub(" ", content)
    text = HTML_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def segments(content):
    text = SHORTCODE_RE.sub("\n", content)
    parts = re.split(r"<[^>]*>|\n", text)
    return [p.strip() for p in parts if len(p.strip()) > 3]


def main(path):
    header, rows = load(path)
    english = [r for r in rows if r[COL_LANG] == "en"]
    langs = sorted({r[COL_LANG] for r in rows} - {"en"})

    print(f"columns              {len(header)}")
    print(f"rows                 {len(rows)}")
    print(f"english pages        {len(english)}")
    print(f"target languages     {len(langs)}  {' '.join(langs)}")

    groups = collections.Counter(r[COL_GROUP] for r in rows)
    translated = {g: n - 1 for g, n in groups.items() if n > 1}
    print(f"translation groups   {len(groups)}")
    print(f"groups with          {len(translated)} -> " +
          ", ".join(f"{g}:{n}" for g, n in sorted(translated.items(), key=lambda kv: -kv[1])))

    missing = sum(len(langs) - translated.get(r[COL_GROUP], 0) for r in english)
    print(f"rows still to make   {missing}")

    print("\n-- duplicate checks")
    for col, name in ((COL_ID, "ID"), (COL_TITLE, "Title"), (COL_SLUG, "Slug"),
                      (COL_IMPORT_KEY, "import_key")):
        counts = collections.Counter(r[col].strip().lower() for r in english if r[col].strip())
        dupes = {k: v for k, v in counts.items() if v > 1}
        print(f"  {name:12} {'clean' if not dupes else dupes}")
    body_hashes = collections.Counter(
        hashlib.md5(r[COL_CONTENT].encode()).hexdigest() for r in english if r[COL_CONTENT].strip())
    print(f"  {'Content':12} {'clean' if not [1 for v in body_hashes.values() if v > 1] else 'DUPLICATES'}")
    print(f"  empty Content {sum(1 for r in english if not r[COL_CONTENT].strip())} pages "
          "(title/SEO/taxonomy still need translating)")
    print(f"  drafts        {sum(1 for r in english if r[COL_STATUS] == 'draft')}")
    print(f"  child pages   {sum(1 for r in english if r[COL_PARENT] not in ('', '0'))}")

    print("\n-- volume")
    words = sum(len(plain_text(r[COL_CONTENT]).split()) for r in english)
    all_segments = [s for r in english for s in segments(r[COL_CONTENT])]
    unique = len(set(all_segments))
    print(f"  body words              {words}")
    print(f"  body words x languages  {words * len(langs)}")
    print(f"  text segments           {len(all_segments)} ({unique} unique, "
          f"{100 * (1 - unique / len(all_segments)):.0f}% cacheable)")

    print("\n-- taxonomy terms to translate")
    for col, name in ((COL_CATS, "Categories"), (COL_TAGS, "Tags"), (COL_RELTAGS, "Relation Tags")):
        terms = {t for r in english for t in r[col].split("|") if t}
        print(f"  {name:14} {len(terms):4} distinct")
    print(f"  {'_g1_subtitle':14} {sum(1 for r in english if r[COL_SUBTITLE].strip()):4} pages")

    print("\n-- markup that must survive verbatim")
    codes = collections.Counter()
    for r in english:
        for m in re.finditer(r"\[/?([a-zA-Z0-9_\-]+)", r[COL_CONTENT]):
            codes[m.group(1)] += 1
    print("  shortcodes:", ", ".join(f"{k}({v})" for k, v in codes.most_common(12)))
    serialized = [i for i, h in enumerate(header)
                  if any(re.match(r"^a:\d+:\{", r[i]) for r in english if r[i])]
    print("  serialised columns:", ", ".join(f"{i}:{header[i]}" for i in serialized))


if __name__ == "__main__":
    main(sys.argv[1])
