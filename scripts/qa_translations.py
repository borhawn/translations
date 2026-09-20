#!/usr/bin/env python3
"""Quality gate on a translation cache, before anything is assembled.

Catches the failure modes a translation worker can actually produce, per
language, without needing the CSV:

    python3 scripts/qa_translations.py --work work --lang de
    python3 scripts/qa_translations.py --work work --all
"""

import argparse
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from units_io import load_cache, load_units
from wpml import langs

ENTITY_RE = re.compile(r"&[a-zA-Z#0-9]+;")
PLACEHOLDER_RE = re.compile(r"\{\{[^{}]*\}\}|%[a-z_]+%|\[/?[a-zA-Z0-9_\-][^\]]*\]")
# Only the rank_math fields are enforced here. Open Graph is not: several of the
# site's own og_title/og_description values already overflow in English, and
# assemble.py falls back to the corrected SEO pair whenever one does.
SEO_LIMITS = {"seo_title": 60, "seo_description": 155}

SCRIPT_RANGES = {
    "arabic": (0x0600, 0x06FF), "cyrillic": (0x0400, 0x04FF),
    "greek": (0x0370, 0x03FF), "hebrew": (0x0590, 0x05FF),
    "devanagari": (0x0900, 0x097F), "thai": (0x0E00, 0x0E7F),
    "japanese": (0x3040, 0x30FF), "korean": (0xAC00, 0xD7AF),
    "chinese": (0x4E00, 0x9FFF),
}

# Short strings that legitimately stay identical in most languages.
PROTECTED_RE = re.compile(
    r"Portugal Quality Control|Portugal|Lisbon\w*|Porto|Braga|Aveiro|Coimbra|"
    r"Leiria|Set\u00fabal|Guimar\u00e3es|Viana do Castelo|Faro|Sines|Leix\u00f5es|"
    r"Marinha Grande|ISO|IATF|SA ?8000|BSCI|SMETA|Sedex|C-?TPAT|GMP|AQL|REACH|"
    r"RoHS|EMC|LVD|CE|EN ?\d+|NDT|CMM|DUPRO|PSI|ANSI|ASQC|MIL[- ]?STD|amfori|CPR|"
    r"Nike|Costco|Walmart|Disney|Tesco|Target|Good Manufacturing Practice|"
    r"Acceptable Quality Limit|Quality Control|\[[^\]]*\]|&[a-zA-Z#0-9]+;|[\W\d_]+",
    re.IGNORECASE)


def unprotected_len(text):
    """Characters left once protected terms and punctuation are removed."""
    return len(PROTECTED_RE.sub("", text).strip())


ALLOWED_IDENTICAL = re.compile(
    r"^(?:[\W\d_]+|[A-Z]{2,6}|ISO\b.*|EN \d+|SA8000|BSCI|SMETA|Sedex|CTPAT|GMP|"
    r"AQL|REACH|RoHS|CE|NDT|CMM|DUPRO|PSI|ANSI|ASQC|MIL-STD|amfori|IATF.*|"
    r"Nike|Costco|Walmart|Disney|Tesco|Target|Portugal.*)$")


def check(work, code, units, verbose=True):
    cache = load_cache(work, code)
    problems = {}

    def bad(kind, detail):
        problems.setdefault(kind, []).append(detail)

    script = SCRIPT_RANGES.get(langs.script(code))
    for i, unit in enumerate(units):
        target = cache.get(unit["uid"])
        if target is None:
            continue
        source = unit["text"]

        if "\r" in target:
            bad("carriage-return-in-translation", i)
        if source.count("\n") != target.count("\n"):
            bad("paragraph-break-count-changed",
                f"{i} (en {source.count(chr(10))} / tr {target.count(chr(10))})")
        if sorted(ENTITY_RE.findall(source)) != sorted(ENTITY_RE.findall(target)):
            bad("html-entities-changed", i)
        if sorted(PLACEHOLDER_RE.findall(source)) != sorted(PLACEHOLDER_RE.findall(target)):
            bad("placeholder-changed", i)
        if not target.strip():
            bad("empty-translation", i)

        limit = SEO_LIMITS.get(unit["kind"])
        if limit and len(html.unescape(target)) > limit:
            bad(f"{unit['kind']}-over-{limit}", f"{i} ({len(html.unescape(target))})")

        if (len(source) > 25 and target == source
                and not ALLOWED_IDENTICAL.match(source.strip())
                and unprotected_len(source) > 12):
            bad("identical-to-english", i)
        # Only meaningful when there is real prose to render in the script.
        if script and unprotected_len(source) > 20 and not any(
                script[0] <= ord(c) <= script[1] for c in target):
            bad("target-script-absent", i)

        # CJK and Thai encode the same meaning in far fewer characters.
        low, high = (0.12, 2.5) if code in langs.CJK else (0.25, 3.0)
        ratio = len(target) / max(len(source), 1)
        if len(source) > 60 and not (low <= ratio <= high):
            bad("suspicious-length-ratio", f"{i} (x{ratio:.1f})")

    done = sum(1 for u in units if u["uid"] in cache)
    total_problems = sum(len(v) for v in problems.values())
    status = "OK" if not problems else "ISSUES"
    print(f"{code:8} {done:5}/{len(units)} ({100*done/len(units):5.1f}%)  "
          f"{status}  {total_problems} problem(s)")
    if verbose:
        for kind, items in sorted(problems.items()):
            shown = ", ".join(str(x) for x in items[:12])
            more = f" ... +{len(items)-12}" if len(items) > 12 else ""
            print(f"    {kind} ({len(items)}): {shown}{more}")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="work")
    ap.add_argument("--lang")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    units = load_units(args.work)
    if args.all:
        d = os.path.join(args.work, "translations")
        codes = sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json")) \
            if os.path.isdir(d) else []
    else:
        codes = [args.lang]

    failed = False
    for code in codes:
        if check(args.work, code, units, verbose=not args.quiet):
            failed = True
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
