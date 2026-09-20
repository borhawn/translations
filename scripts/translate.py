#!/usr/bin/env python3
"""Steps 5-6 — translate the extracted units into one or more languages.

Resumable: every translated unit is written to a per-language cache keyed on the
source hash, so re-running only fills the gaps. Kill it and restart at will.

    export ANTHROPIC_API_KEY=sk-ant-...
    python3 scripts/translate.py --langs de --work work
    python3 scripts/translate.py --langs all --work work --concurrency 4

--engine mock produces deterministic fake output for pipeline testing.
"""

import argparse
import html
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wpml import langs, prompts

MODEL = "claude-opus-5"

# RankMath's budgets. Translations routinely run 10-30% longer than the English
# source, so the limit has to be enforced in the target language, not the source.
LENGTH_LIMITS = {"seo_title": 60, "og_title": 60,
                 "seo_description": 155, "og_description": 155}
BATCH_CHARS = 6000          # per request, keeps responses well inside limits
BATCH_ITEMS = 40
MAX_RETRIES = 4


def load_units(work):
    with open(os.path.join(work, "units.jsonl"), encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def cache_path(work, code):
    return os.path.join(work, "translations", f"{code}.json")


def load_cache(work, code):
    path = cache_path(work, code)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save_cache(work, code, cache):
    path = cache_path(work, code)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=0, sort_keys=True)
    os.replace(tmp, path)


def batches(units):
    """Group by kind, then by size, so each request has one clear instruction."""
    by_kind = {}
    for unit in units:
        by_kind.setdefault(unit["kind"], []).append(unit)
    for kind, group in by_kind.items():
        group.sort(key=lambda u: len(u["text"]))
        current, size = [], 0
        for unit in group:
            if current and (size + len(unit["text"]) > BATCH_CHARS
                            or len(current) >= BATCH_ITEMS):
                yield kind, current
                current, size = [], 0
            current.append(unit)
            size += len(unit["text"])
        if current:
            yield kind, current


class MockEngine:
    """Deterministic stand-in: proves the pipeline without spending anything."""
    def __call__(self, code, kind, items, glossary):
        return {uid: f"\u00ab{code}\u00bb {text}" for uid, text in items}


class ClaudeEngine:
    def __init__(self, model=MODEL):
        import anthropic
        self.client = anthropic.Anthropic()
        self.model = model

    def __call__(self, code, kind, items, glossary):
        out = self._translate(code, kind, items, glossary)
        limit = LENGTH_LIMITS.get(kind)
        if limit:
            out = self._enforce_length(code, kind, items, glossary, out, limit)
        return out

    def _enforce_length(self, code, kind, items, glossary, out, limit):
        """Re-ask for anything that overflowed, with the budget spelled out."""
        source = dict(items)
        for _ in range(2):
            over = [(uid, text) for uid, text in out.items()
                    if len(html.unescape(text)) > limit]
            if not over:
                break
            retry = [(uid, source[uid]) for uid, _ in over if uid in source]
            instruction = (
                f"These {kind} translations came back too long. Rewrite each one "
                f"in {langs.name(code)} so it is at most {limit} characters, "
                "counting every character including spaces. Keep the meaning and "
                "the keyword; drop qualifiers and shorten phrasing to fit. "
                "Return the same id<TAB>text format.")
            fixed = self._translate(code, kind, retry, glossary, prefix=instruction)
            improved = {uid: txt for uid, txt in fixed.items()
                        if len(html.unescape(txt)) < len(html.unescape(out[uid]))}
            if not improved:
                break
            out.update(improved)
        return out

    def _translate(self, code, kind, items, glossary, prefix=None):
        system = prompts.system_prompt(code)
        user = prompts.user_prompt(code, kind, items, glossary)
        if prefix:
            user = prefix + "\n\n" + user
        expected = [uid for uid, _ in items]
        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=8000,
                    system=[{"type": "text", "text": system,
                             "cache_control": {"type": "ephemeral"}}],
                    messages=[{"role": "user", "content": user}],
                )
                text = "".join(b.text for b in response.content if b.type == "text")
                out, problems = prompts.parse_response(text, expected)
                if not problems:
                    return out
                # Retry only what came back missing.
                items = [(uid, txt) for uid, txt in items if uid not in out]
                expected = [uid for uid, _ in items]
                if not items:
                    return out
            except Exception as exc:                       # noqa: BLE001
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(2 ** attempt)
        return out


def translate_language(code, units, glossary, engine, work, verbose=True):
    cache = load_cache(work, code)
    todo = [u for u in units if u["uid"] not in cache]
    if not todo:
        if verbose:
            print(f"{code}: already complete ({len(cache)} units)")
        return cache
    done = 0
    for kind, batch in batches(todo):
        items = [(u["uid"], u["text"]) for u in batch]
        result = engine(code, kind, items, glossary)
        cache.update(result)
        done += len(result)
        save_cache(work, code, cache)
        if verbose:
            print(f"{code}: {done}/{len(todo)} ({kind})", flush=True)
    missing = [u["uid"] for u in units if u["uid"] not in cache]
    if missing:
        print(f"{code}: WARNING {len(missing)} units still untranslated", file=sys.stderr)
    return cache


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="work")
    ap.add_argument("--langs", default="all", help="comma-separated codes, or 'all'")
    ap.add_argument("--engine", choices=("claude", "mock"), default="claude")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--concurrency", type=int, default=1)
    args = ap.parse_args()

    codes = langs.CODES if args.langs == "all" else args.langs.split(",")
    unknown = [c for c in codes if c not in langs.LANGUAGES]
    if unknown:
        sys.exit(f"unknown language codes: {unknown}")

    units = load_units(args.work)
    engine = MockEngine() if args.engine == "mock" else ClaudeEngine(args.model)

    def run(code):
        glossary_file = os.path.join(args.work, "glossary", f"{code}.json")
        glossary = {}
        if os.path.exists(glossary_file):
            with open(glossary_file, encoding="utf-8") as fh:
                glossary = json.load(fh)
        translate_language(code, units, glossary, engine, args.work,
                           verbose=args.concurrency == 1)
        return code

    if args.concurrency > 1:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            for code in pool.map(run, codes):
                print(f"{code}: done", flush=True)
    else:
        for code in codes:
            run(code)


if __name__ == "__main__":
    main()
