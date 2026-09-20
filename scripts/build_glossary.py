#!/usr/bin/env python3
"""Step 3/5 — the term glossary, translated once and reused by every page.

Pass 1 (no --langs) writes work/glossary/en.json: the taxonomy terms plus the
recurring phrases worth pinning down. Pass 2 translates it per language. Review
work/glossary/<lang>.json before running the page translation — every page
inherits these renderings.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wpml import export as E, langs, prompts
from translate import ClaudeEngine, MockEngine

# Phrases that must read identically everywhere they appear.
PINNED = [
    "Quality Inspection", "Quality Control", "Factory Audit", "Vendor Audit",
    "Supplier Evaluation", "Pre-Shipment Inspection", "During Production Inspection",
    "Initial Production Inspection", "Production Monitoring", "Defect Sorting",
    "Container Loading Inspection", "Cargo Survey", "Full Inspection",
    "Dimensional Inspection", "Product Testing", "Social Audit",
    "Supply Chain", "Importer", "Buyer", "Supplier", "Vendor", "Inspector",
    "Auditor", "Defect", "Compliance", "Certification", "Checklist",
    "Third-party inspection", "Quality Assurance", "Corrective Action",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?")
    ap.add_argument("--work", default="work")
    ap.add_argument("--langs", help="comma-separated codes, or 'all'")
    ap.add_argument("--engine", choices=("claude", "mock"), default="claude")
    args = ap.parse_args()

    out_dir = os.path.join(args.work, "glossary")
    os.makedirs(out_dir, exist_ok=True)
    source_path = os.path.join(out_dir, "en.json")

    if not args.langs:
        if not args.csv:
            sys.exit("pass the export CSV to build the English glossary")
        ex = E.load(args.csv)
        terms = set(PINNED)
        for row in ex.english:
            for col in (E.CATEGORIES, E.TAGS, E.RELATION_TAGS):
                terms.update(t.strip() for t in row[col].split("|") if t.strip())
        terms = sorted(terms, key=str.lower)
        with open(source_path, "w", encoding="utf-8") as fh:
            json.dump(terms, fh, ensure_ascii=False, indent=1)
        print(f"{len(terms)} glossary terms -> {source_path}")
        return

    with open(source_path, encoding="utf-8") as fh:
        terms = json.load(fh)
    codes = langs.CODES if args.langs == "all" else args.langs.split(",")
    engine = MockEngine() if args.engine == "mock" else ClaudeEngine()

    for code in codes:
        path = os.path.join(out_dir, f"{code}.json")
        done = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
        todo = [t for t in terms if t not in done]
        for start in range(0, len(todo), 50):
            chunk = todo[start:start + 50]
            items = [(str(i), t) for i, t in enumerate(chunk)]
            result = engine(code, "term", items, {})
            for i, term in items:
                if i in result:
                    done[term] = result[i]
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(done, fh, ensure_ascii=False, indent=1, sort_keys=True)
        print(f"{code}: {len(done)}/{len(terms)} terms")


if __name__ == "__main__":
    main()
