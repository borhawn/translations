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
# An "&word" that never closes with a semicolon: a corrupted entity.
MALFORMED_ENTITY_RE = re.compile(r"&[a-zA-Z#0-9]{2,8}(?![a-zA-Z#0-9]*;)")
PLACEHOLDER_RE = re.compile(r"\{\{[^{}]*\}\}|%[a-z_]+%|\[/?[a-zA-Z0-9_\-][^\]]*\]")
# Only the rank_math fields are enforced here. Open Graph is not: several of the
# site's own og_title/og_description values already overflow in English, and
# assemble.py falls back to the corrected SEO pair whenever one does.
SEO_LIMITS = {"seo_title": 60, "seo_description": 155}

SCRIPT_RANGES = {
    "arabic":     [(0x0600, 0x06FF), (0x0750, 0x077F)],
    "cyrillic":   [(0x0400, 0x04FF)],
    "greek":      [(0x0370, 0x03FF), (0x1F00, 0x1FFF)],
    "hebrew":     [(0x0590, 0x05FF)],
    "devanagari": [(0x0900, 0x097F)],
    "thai":       [(0x0E00, 0x0E7F)],
    # Japanese prose is routinely pure kanji, so the CJK ideograph block counts.
    "japanese":   [(0x3040, 0x30FF), (0x4E00, 0x9FFF), (0x3400, 0x4DBF)],
    # Korean uses Hangul, and Hanja still appears in technical copy.
    "korean":     [(0xAC00, 0xD7AF), (0x1100, 0x11FF), (0x4E00, 0x9FFF)],
    "chinese":    [(0x4E00, 0x9FFF), (0x3400, 0x4DBF)],
}


def in_script(text, ranges):
    return any(lo <= ord(c) <= hi for c in text for lo, hi in ranges)

# Short strings that legitimately stay identical in most languages.
# Terms that legitimately survive untranslated. Built longest-first, because
# Python alternation is leftmost-first: with "Sedex" before "Sedex Members
# Ethical Trade Audit", the short branch wins and the rest looks untranslated.
_PROTECTED_TERMS = [
    # Scheme and standards-body names, kept in English beside their acronym.
    "International Electrotechnical Commission",
    "International Organization for Standardization",
    "Registration, Evaluation, Authorisation and Restriction of Chemicals",
    "Registration Evaluation Authorisation and Restriction of Chemicals",
    "Global Standard for Packaging and Packaging Materials",
    "Hazard Analysis and Critical Control Points",
    "Customs-Trade Partnership Against Terrorism",
    "Customs Trade Partnership Against Terrorism",
    "Business Social Compliance Initiative",
    "Sedex Members Ethical Trade Audit",
    "Social Accountability International",
    "Restriction of Hazardous Substances",
    "Good Manufacturing Practice",
    "Responsible Down Standard",
    "Global Recycled Standard",
    "Acceptable Quality Limit",
    "DesignLights Consortium",
    "CEC Title 20 and Title 24",
    "AP (Approved Product) Seal",
    "Approved Product",
    "Conformit\u00e9 Europ\u00e9enne",
    "Quality Control", "Energy Star", "Marinha Grande", "Viana do Castelo",
    "Portugal Quality Control",
    # Companies, places, acronyms.
    "OEKO-TEX", "BLUESIGN", "Intertek", "amfori", "Walmart", "Costco",
    "Disney", "Tesco", "Target", "Nike", "Sedex", "SMETA", "BSCI", "CTPAT",
    "C-TPAT", "SA8000", "SA 8000", "IATF", "ISO", "GMP", "AQL", "REACH",
    "RoHS", "EMC", "LVD", "NDT", "CMM", "DUPRO", "PSI", "ANSI", "ASQC",
    "MIL-STD", "MIL STD", "CPR", "GOTS", "FSC", "PEFC", "BRC", "IFS",
    "HACCP", "FDA", "LFGB", "ASTM", "DIN", "UNE", "JIS", "SGS", "VDE",
    "ETL", "UL", "CE", "GB", "NF",
    "Lisbonne", "Lisbon", "Porto", "Braga", "Aveiro", "Coimbra", "Leiria",
    "Set\u00fabal", "Guimar\u00e3es", "Leix\u00f5es", "Sines", "Faro", "Portugal",
    "Standards", "Standard",
]

PROTECTED_RE = re.compile(
    "|".join(sorted((re.escape(t) for t in _PROTECTED_TERMS), key=len, reverse=True))
    + r"|EN ?\d+|\[[^\]]*\]|&[a-zA-Z#0-9]+;|[\W\d_]+",
    re.IGNORECASE)


def unprotected_len(text):
    """Characters left once protected terms and punctuation are removed."""
    return len(PROTECTED_RE.sub("", text).strip())


# Media library entries are image filenames, not prose.
FILENAME_RE = re.compile(r"^[\w.-]+$")

# An acronym expansion sits next to its acronym, which the markup splits off:
# "(Global Organic Textile Standard)", "Better Cotton Initiative (".
# These are registered scheme names and stay in English in every language.
_MINOR = {"of", "and", "for", "the", "in", "on", "to", "a", "an"}


def is_title_case_name(text):
    words = re.findall(r"[A-Za-z][\w'-]*", text.strip())
    return (len(words) >= 2
            and all(w[0].isupper() or w.lower() in _MINOR for w in words))


BARE_ACRONYM_RE = re.compile(r"^[A-Z][A-Z0-9/&.-]{1,9}$")


def is_scheme_name(text, next_text="", prev_text=""):
    """A registered scheme name, kept in English in every language.

    The markup splits an expansion from its acronym, and either side can land
    in a neighbouring unit:
      "(Global Organic Textile Standard)"  - parenthesis in this unit
      "Better Cotton Initiative ("         - opening parenthesis trails
      "Forest Stewardship Council"         - followed by "(FSC) Certification"
      "Boiler and Pressure Vessel Code"    - preceded by the acronym "ASME"
    """
    stripped = text.strip()
    if not is_title_case_name(stripped):
        return False
    if (stripped.startswith("(") or stripped.endswith("(")
            or stripped.endswith(")")):
        return True
    if next_text.strip().startswith("("):
        return True
    return bool(BARE_ACRONYM_RE.match(prev_text.strip()))


ALLOWED_IDENTICAL = re.compile(
    r"^(?:[\W\d_]+|[A-Z]{2,6}|ISO\b.*|EN \d+|SA8000|BSCI|SMETA|Sedex|CTPAT|GMP|"
    r"AQL|REACH|RoHS|CE|NDT|CMM|DUPRO|PSI|ANSI|ASQC|MIL-STD|amfori|IATF.*|"
    r"Nike|Costco|Walmart|Disney|Tesco|Target|Portugal.*)$")


def load_exceptions(work):
    path = os.path.join(work, "qa-exceptions.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def check(work, code, units, verbose=True):
    cache = load_cache(work, code)
    accepted = load_exceptions(work).get(code, {})
    problems = {}

    def bad(kind, detail):
        index = str(detail).split(" ")[0]
        entry = accepted.get(index)
        if entry and entry.get("check") == kind:
            return
        problems.setdefault(kind, []).append(detail)

    script = SCRIPT_RANGES.get(langs.script(code))
    for i, unit in enumerate(units):
        target = cache.get(unit["uid"])
        if target is None:
            continue
        source = unit["text"]
        next_source = units[i + 1]["text"] if i + 1 < len(units) else ""
        prev_source = units[i - 1]["text"] if i else ""

        if "\r" in target:
            bad("carriage-return-in-translation", i)
        if source.count("\n") != target.count("\n"):
            bad("paragraph-break-count-changed",
                f"{i} (en {source.count(chr(10))} / tr {target.count(chr(10))})")
        # Dropping an entity is a legitimate translation choice - Japanese
        # renders "Materials &amp; Commodities" as 原材料・コモディティ, with no
        # ampersand at all. Inventing one the source does not have is the real
        # error, and so is emitting a malformed &xxx sequence.
        source_entities = set(ENTITY_RE.findall(source))
        invented = set(ENTITY_RE.findall(target)) - source_entities
        if invented:
            bad("html-entity-invented", f"{i} {sorted(invented)}")
        if MALFORMED_ENTITY_RE.search(target):
            bad("malformed-entity", i)
        if sorted(PLACEHOLDER_RE.findall(source)) != sorted(PLACEHOLDER_RE.findall(target)):
            bad("placeholder-changed", i)
        if not target.strip():
            bad("empty-translation", i)

        limit = SEO_LIMITS.get(unit["kind"])
        if limit and len(html.unescape(target)) > limit:
            bad(f"{unit['kind']}-over-{limit}", f"{i} ({len(html.unescape(target))})")

        if (len(source) > 25 and target == source
                and not ALLOWED_IDENTICAL.match(source.strip())
                and not is_scheme_name(source, next_source, prev_source)
                and unprotected_len(source) > 12):
            bad("identical-to-english", i)
        # Only meaningful when there is real prose to render in the script.
        if (script and unprotected_len(source) > 20
                and not FILENAME_RE.match(source.strip())
                and not is_scheme_name(source, next_source, prev_source)
                and not in_script(target, script)):
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
