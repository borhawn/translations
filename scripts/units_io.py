#!/usr/bin/env python3
"""Hand-translation helpers: print numbered slices, ingest TSV back.

The pipeline's cache is keyed on a 16-char source hash. Writing those by hand
would cost more characters than the translations themselves, so translations are
exchanged as `index<TAB>text` against a stable ordering of units.jsonl.

    python3 scripts/units_io.py list  --work work --from 0 --count 200
    python3 scripts/units_io.py todo  --work work --lang de
    python3 scripts/units_io.py add   --work work --lang de --tsv batch.tsv
    python3 scripts/units_io.py stats --work work
"""

import argparse
import json
import os
import sys


def encode(text):
    """Newlines inside a unit would break the line-based exchange format."""
    return text.replace("\\", "\\\\").replace("\r\n", "\\n").replace("\n", "\\n").replace("\t", " ")


def decode(text):
    out, i = [], 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            if nxt == "n":
                out.append("\n"); i += 2; continue
            if nxt == "\\":
                out.append("\\"); i += 2; continue
        out.append(text[i]); i += 1
    return "".join(out)


def load_units(work):
    with open(os.path.join(work, "units.jsonl"), encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def cache_file(work, lang):
    return os.path.join(work, "translations", f"{lang}.json")


def load_cache(work, lang):
    path = cache_file(work, lang)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save_cache(work, lang, cache):
    path = cache_file(work, lang)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=0, sort_keys=True)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("list", "todo", "add", "stats"))
    ap.add_argument("--work", default="work")
    ap.add_argument("--lang")
    ap.add_argument("--tsv")
    ap.add_argument("--from", dest="start", type=int, default=0)
    ap.add_argument("--count", type=int, default=200)
    ap.add_argument("--to", dest="end", type=int, default=None,
                    help="inclusive last index; overrides --count")
    ap.add_argument("--missing", action="store_true",
                    help="with --lang, list only units not yet translated")
    ap.add_argument("--max-chars", type=int, default=0)
    args = ap.parse_args()

    units = load_units(args.work)

    if args.action == "list":
        end = (args.end + 1) if args.end is not None else args.start + args.count
        end = min(end, len(units))
        cache = load_cache(args.work, args.lang) if (args.missing and args.lang) else None
        total = printed = 0
        for i in range(args.start, end):
            if cache is not None and units[i]["uid"] in cache:
                continue
            text = units[i]["text"]
            if args.max_chars and total + len(text) > args.max_chars and printed:
                break
            print(f"{i}\t{encode(text)}")
            total += len(text)
            printed += 1
        return

    if args.action == "todo":
        cache = load_cache(args.work, args.lang)
        missing = [i for i, u in enumerate(units) if u["uid"] not in cache]
        print(f"{args.lang}: {len(cache)}/{len(units)} done, {len(missing)} missing")
        if missing:
            print(f"next index {missing[0]}, last missing {missing[-1]}")
        return

    if args.action == "add":
        cache = load_cache(args.work, args.lang)
        added = skipped = 0
        with open(args.tsv, encoding="utf-8") as fh:
            for line in fh:
                line = line.rstrip("\n")
                if not line or "\t" not in line:
                    continue
                index, _, text = line.partition("\t")
                try:
                    unit = units[int(index)]
                except (ValueError, IndexError):
                    print(f"bad index: {index!r}", file=sys.stderr)
                    skipped += 1
                    continue
                if not text.strip():
                    skipped += 1
                    continue
                cache[unit["uid"]] = decode(text)
                added += 1
        save_cache(args.work, args.lang, cache)
        print(f"{args.lang}: +{added} (skipped {skipped}) -> {len(cache)}/{len(units)}")
        return

    if args.action == "stats":
        print(f"units {len(units)}  chars {sum(len(u['text']) for u in units):,}")
        d = os.path.join(args.work, "translations")
        for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if name.endswith(".json"):
                lang = name[:-5]
                n = len(load_cache(args.work, lang))
                print(f"  {lang:8} {n:5}/{len(units)}  {100*n/len(units):5.1f}%")


if __name__ == "__main__":
    main()
