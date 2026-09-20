# Translation progress and how to continue

No API key is available, so translations are produced by Claude workers writing
into `work/translations/<lang>.json`. Everything is committed, and the cache is
keyed on the SHA-1 of the source string, so **work is never repeated** — a new
session picks up exactly where the last one stopped.

## Check the state

```bash
python3 scripts/units_io.py stats --work work          # coverage per language
python3 scripts/qa_translations.py --work work --all   # quality gate
python3 scripts/plan_waves.py --work work --lang de    # remaining agent ranges
```

## Dispatch more work

One worker per language per ~800-unit range; roughly 7 ranges cover a language,
so all 37 languages is ~259 worker runs. Each worker:

1. reads `docs/translator-brief.md`,
2. loops `units_io.py list --missing --from A --to B --max-chars 7000`
   → translate → quoted heredoc TSV → `units_io.py add`,
3. finishes with `qa_translations.py --lang <code>` and fixes its own range.

Workers must not run git commands and must touch only their own language, so
several can run concurrently without conflicting — each language is a separate
file.

## Assemble and validate a finished language

A language is deployable as soon as it is complete; it does not wait for the
other 36.

```bash
python3 scripts/assemble.py source-export.csv --work work --out de.csv --langs de
python3 scripts/validate.py de.csv --source source-export.csv
```

Then import per `docs/pipeline.md` (two passes, unique key `import_key`).

## Decisions already settled

* SEO: option B — English baseline written and reviewed in `seo/en.json`, then
  translated. 111 pages written from scratch, 8 rewritten to fit Google's
  limits.
* Slugs: WordPress's own behaviour, as the homepage shows.
* Rev Slider: the English parent's alias in every language.
* Image `alt`/`title`: not translated.
* Source content bugs are **not** fixed — they are translated as they are. The
  known ones are listed at the end of `docs/pipeline.md`.

## Accepted QA findings

`work/qa-exceptions.json` records findings that are understood and accepted,
each with a written reason. Anything not listed there is a real problem.
