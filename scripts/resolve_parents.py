#!/usr/bin/env python3
"""Step 10, pass 2 — give the translated child pages their translated parent.

48 of the 119 English pages have a parent. A German child must point at the
German parent, whose post ID does not exist until pass 1 has run. So pass 1
imports everything flat, and this builds the small update-only file that sets
the hierarchy.

Input is whatever tells us import_key -> new post ID:
  * a fresh export of all pages (same exporter as the original), or
  * a two-column CSV: import_key,post_id

    python3 scripts/resolve_parents.py export-after-pass1.csv \\
        --source original-export.csv --out parents.csv
"""

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wpml import export as E

csv.field_size_limit(10 ** 9)


def load_id_map(path):
    """{import_key: post_id} from a full re-export or a two-column CSV."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    header = rows[0]
    if len(header) == E.EXPECTED_COLUMNS:
        return {r[E.IMPORT_KEY]: r[E.ID] for r in rows[1:] if r[E.IMPORT_KEY].strip()}
    if len(header) == 2:
        start = 1 if not header[1].strip().isdigit() else 0
        return {r[0].strip(): r[1].strip() for r in rows[start:] if r[0].strip()}
    sys.exit(f"{path}: expected the {E.EXPECTED_COLUMNS}-column export or a "
             f"two-column import_key,post_id file; found {len(header)} columns")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("after_pass1", help="re-export, or import_key,post_id CSV")
    ap.add_argument("--source", required=True, help="the original English export")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    id_map = load_id_map(args.after_pass1)
    ex = E.load(args.source)
    english = {r[E.ID]: r for r in ex.english}
    slug_of = {}                                    # (en_id, lang) -> slug

    if len(open(args.after_pass1, encoding="utf-8-sig").readline().split(",")) > 2:
        with open(args.after_pass1, newline="", encoding="utf-8-sig") as fh:
            reader = csv.reader(fh)
            next(reader)
            for row in reader:
                if row[E.IMPORT_KEY].strip():
                    slug_of[row[E.IMPORT_KEY]] = row[E.SLUG]

    rows, unresolved = [], []
    for key, post_id in sorted(id_map.items()):
        en_id, _, code = key.rpartition("-")
        source = english.get(en_id)
        if source is None or code == "en":
            continue
        parent_en = source[E.PARENT]
        if parent_en in ("", "0"):
            continue
        parent_key = f"{parent_en}-{code}"
        parent_id = id_map.get(parent_key)
        if not parent_id:
            unresolved.append(f"{key}: no {parent_key} in the ID map")
            continue
        rows.append([key, parent_id, slug_of.get(parent_key, "")])

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        writer.writerow(["import_key", "Parent", "Parent Slug"])
        writer.writerows(rows)

    print(f"child pages to re-parent: {len(rows)} -> {args.out}")
    if unresolved:
        print(f"\nUNRESOLVED ({len(unresolved)}) — these parents were not imported:",
              file=sys.stderr)
        for line in unresolved[:10]:
            print(f"  {line}", file=sys.stderr)
        sys.exit(1)
    print("import this as an update-only run matched on import_key, "
          "mapping Parent (and Parent Slug if your importer uses it).")


if __name__ == "__main__":
    main()
