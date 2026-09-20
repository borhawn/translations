#!/usr/bin/env python3
"""Detect translations attached to the wrong source unit.

An off-by-one slip in the index<TAB>text exchange produces translations that
are individually valid but describe the wrong thing. qa_translations.py cannot
see it, because nothing about any single line is malformed.

This is tuned for precision, not recall. The only signal used is DIGITS: a
number in the source almost always appears unchanged in the translation, and
unlike vocabulary it is not affected by word order, compounding or case. A unit
is reported only when its own digits disagree with the source AND a neighbouring
source matches them exactly - the pattern a shift produces and an ordinary
translation choice does not.

    python3 scripts/check_alignment.py --work work --all
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from units_io import load_cache, load_units

DIGITS_RE = re.compile(r"\d+")

# Numbers that carry no positional meaning: they appear in boilerplate on many
# pages, so matching them says nothing about alignment.
UBIQUITOUS = {"24", "48", "100", "1", "2", "3"}


def digits(text):
    return frozenset(DIGITS_RE.findall(text)) - UBIQUITOUS


def check(work, code, units, window=3):
    cache = load_cache(work, code)
    suspects = []
    for i, unit in enumerate(units):
        target = cache.get(unit["uid"])
        if target is None:
            continue
        source_digits = digits(unit["text"])
        if not source_digits:
            continue
        target_digits = digits(target)
        if source_digits == target_digits:
            continue
        neighbours = [
            offset for offset in range(-window, window + 1)
            if offset and 0 <= i + offset < len(units)
            and digits(units[i + offset]["text"]) == target_digits
            and digits(units[i + offset]["text"])
        ]
        suspects.append((i, sorted(source_digits), sorted(target_digits), neighbours))

    shifted = [s for s in suspects if s[3]]
    print(f"{code:8} {len(suspects):3} digit mismatches, "
          f"{len(shifted):3} matching a neighbour (likely shift)")
    for i, src, tgt, neigh in shifted[:20]:
        print(f"    index {i}: source {src} vs translation {tgt}, "
              f"neighbour offset {neigh}")
        print(f"      EN: {units[i]['text'][:90]}")
        print(f"      TR: {cache[units[i]['uid']][:90]}")
    for i, src, tgt, _ in [s for s in suspects if not s[3]][:8]:
        print(f"    (review) index {i}: source {src} vs translation {tgt}")
        print(f"      EN: {units[i]['text'][:90]}")
        print(f"      TR: {cache[units[i]['uid']][:90]}")
    return shifted


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="work")
    ap.add_argument("--lang")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    units = load_units(args.work)
    d = os.path.join(args.work, "translations")
    codes = sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json")) \
        if args.all else [args.lang]
    bad = False
    for code in codes:
        if check(args.work, code, units):
            bad = True
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
