#!/usr/bin/env python3
"""Step 7/9 — refuse to ship a file that would break the site.

Runs over an assembled import CSV and checks every generated row against its
English source. Exits non-zero if anything fails.

    python3 scripts/validate.py import.csv --source export.csv
"""

import argparse
import collections
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wpml import export as E, langs, markup as M, phpserial as PS

SEO_TITLE_MAX = 60
SEO_DESC_MAX = 155
SERIAL_COLUMNS = (24, 25, 30, 32, 35, 37, 39, 53, 54, 55, 56)

# Script ranges used to catch "translated" text that is still English.
SCRIPT_RANGES = {
    "arabic": (0x0600, 0x06FF), "cyrillic": (0x0400, 0x04FF),
    "greek": (0x0370, 0x03FF), "hebrew": (0x0590, 0x05FF),
    "devanagari": (0x0900, 0x097F), "thai": (0x0E00, 0x0E7F),
    "japanese": (0x3040, 0x30FF), "korean": (0xAC00, 0xD7AF),
    "chinese": (0x4E00, 0x9FFF),
}


class Report:
    def __init__(self):
        self.failures = collections.defaultdict(list)
        self.counts = collections.Counter()

    def fail(self, check, detail):
        self.failures[check].append(detail)

    def ok(self, check):
        self.counts[check] += 1


def visible(text):
    return len(html.unescape(text))


def has_target_script(text, code):
    span = SCRIPT_RANGES.get(langs.script(code))
    if not span:
        return True
    return any(span[0] <= ord(c) <= span[1] for c in text)


def check_row(row, source, report):
    code = row[E.LANG]
    key = row[E.IMPORT_KEY] or f"{row[E.WPML_TRANSLATION_ID]}-{code}"

    # --- WPML group wiring
    if row[E.ID].strip():
        report.fail("id-must-be-empty", key)
    if row[E.GROUP] != source[E.GROUP] or row[E.GROUP_2] != row[E.GROUP]:
        report.fail("group-mismatch", key)
    if row[E.WPML_TRANSLATION_ID] != source[E.ID]:
        report.fail("translation-id-mismatch", key)
    if not (row[E.LANG] == row[E.IMPORT_LANG] == row[E.IMPORT_LANG_2] == code):
        report.fail("language-columns-disagree", key)
    if row[E.IMPORT_SRC_LANG] != "en" or row[E.IMPORT_SRC_LANG_2] != "en":
        report.fail("source-language-not-en", key)
    if row[E.LANG_DUPLICATE_OF].strip():
        report.fail("lang-duplicate-of-must-be-empty", key)
    report.ok("wpml-wiring")

    # --- markup survived untouched
    if M.markup_signature(row[E.CONTENT]) != M.markup_signature(source[E.CONTENT]):
        report.fail("markup-sequence-changed", key)
    else:
        report.ok("markup-sequence")
    if M.entity_signature(row[E.CONTENT]) != M.entity_signature(source[E.CONTENT]):
        report.fail("html-entities-changed", key)
    else:
        report.ok("html-entities")

    # --- serialized blobs still parse, with correct byte lengths
    for col in SERIAL_COLUMNS:
        value = row[col]
        if not value.strip():
            continue
        try:
            if PS.dumps(PS.loads(value)) != value:
                report.fail("serialized-not-canonical", f"{key} col{col}")
            else:
                report.ok("serialized")
        except Exception as exc:                            # noqa: BLE001
            report.fail("serialized-unparseable", f"{key} col{col}: {exc}")

    # --- taxonomy shape
    for col, name in ((E.CATEGORIES, "categories"), (E.TAGS, "tags"),
                      (E.RELATION_TAGS, "relation_tags")):
        if len(row[col].split("|")) != len(source[col].split("|")):
            report.fail(f"{name}-count-changed", key)
    report.ok("taxonomy-shape")

    # --- SEO budgets, measured in the target language
    if row[E.SEO_TITLE] and visible(row[E.SEO_TITLE]) > SEO_TITLE_MAX:
        report.fail("seo-title-too-long",
                    f"{key} {visible(row[E.SEO_TITLE])} chars")
    if row[E.SEO_DESC] and visible(row[E.SEO_DESC]) > SEO_DESC_MAX:
        report.fail("seo-description-too-long",
                    f"{key} {visible(row[E.SEO_DESC])} chars")
    report.ok("seo-length")

    # --- did anything actually get translated?
    if source[E.TITLE].strip() and row[E.TITLE] == source[E.TITLE]:
        report.fail("title-untranslated", key)
    # A body made only of shortcodes (e.g. "[glossary]") has nothing to translate.
    if M.translatable(M.tokenize(source[E.CONTENT])) and row[E.CONTENT] == source[E.CONTENT]:
        report.fail("body-untranslated", key)
    if len(row[E.TITLE]) > 8 and not has_target_script(row[E.TITLE], code):
        report.fail("wrong-script", f"{key}: {row[E.TITLE][:40]}")
    report.ok("translated")

    # --- slug
    if not row[E.SLUG].strip():
        report.fail("empty-slug", key)
    elif not re.fullmatch(r"[a-z0-9%\-]+", row[E.SLUG]):
        report.fail("invalid-slug-characters", f"{key}: {row[E.SLUG]}")
    report.ok("slug")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--source", required=True)
    ap.add_argument("--json", help="write the full report here")
    args = ap.parse_args()

    result = E.load(args.csv)
    original = E.load(args.source)
    original_keys = {(r[E.GROUP], r[E.LANG]) for r in original.rows}
    english = {r[E.ID]: r for r in original.english}

    report = Report()
    generated = [r for r in result.rows
                 if (r[E.GROUP], r[E.LANG]) not in original_keys]

    print(f"rows in file {len(result.rows)}  original {len(original.rows)}  "
          f"generated {len(generated)}")

    for row in generated:
        source = english.get(row[E.WPML_TRANSLATION_ID])
        if source is None:
            report.fail("no-english-source", row[E.IMPORT_KEY])
            continue
        check_row(row, source, report)

    # --- file-level invariants
    keys = collections.Counter(r[E.IMPORT_KEY] for r in result.rows if r[E.IMPORT_KEY])
    for key, count in keys.items():
        if count > 1:
            report.fail("duplicate-import-key", f"{key} x{count}")
    pairs = collections.Counter((r[E.GROUP], r[E.LANG]) for r in result.rows)
    for pair, count in pairs.items():
        if count > 1:
            report.fail("duplicate-group-language", f"{pair} x{count}")
    for code in {r[E.LANG] for r in generated}:
        slug_counts = collections.Counter(
            r[E.SLUG] for r in result.rows if r[E.LANG] == code and r[E.SLUG])
        for slug, count in slug_counts.items():
            if count > 1:
                report.fail("duplicate-slug-in-language", f"{code}/{slug} x{count}")

    print("\nchecks passed:")
    for check, count in sorted(report.counts.items()):
        print(f"  {check:22} {count}")

    if report.failures:
        print("\nFAILURES:")
        for check, details in sorted(report.failures.items()):
            print(f"  {check} ({len(details)})")
            for detail in details[:5]:
                print(f"      {detail}")
            if len(details) > 5:
                print(f"      ... and {len(details) - 5} more")
    else:
        print("\nno failures")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"counts": dict(report.counts),
                       "failures": {k: v for k, v in report.failures.items()}},
                      fh, ensure_ascii=False, indent=1)

    sys.exit(1 if report.failures else 0)


if __name__ == "__main__":
    main()
