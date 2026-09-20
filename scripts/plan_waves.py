#!/usr/bin/env python3
"""Split the remaining work for a language into agent-sized ranges."""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from units_io import load_cache, load_units

ap = argparse.ArgumentParser()
ap.add_argument("--work", default="work")
ap.add_argument("--lang", required=True)
ap.add_argument("--size", type=int, default=800, help="units per agent")
args = ap.parse_args()

units = load_units(args.work)
cache = load_cache(args.work, args.lang)
missing = [i for i, u in enumerate(units) if u["uid"] not in cache]
if not missing:
    print(f"{args.lang}: complete")
    sys.exit()
ranges, start = [], missing[0]
for i in range(0, len(missing), args.size):
    chunk = missing[i:i + args.size]
    ranges.append((chunk[0], chunk[-1], len(chunk),
                   sum(len(units[j]["text"]) for j in chunk)))
print(f"{args.lang}: {len(missing)} units missing, {len(ranges)} agent ranges")
for lo, hi, n, chars in ranges:
    print(f"  --from {lo} --to {hi}   ({n} units, {chars:,} chars)")
