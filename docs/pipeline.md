# Running the pipeline

Decisions locked in (see `docs/analysis.md` §5–§7 for why each one matters):

| | |
|---|---|
| **SEO** | Option B — English baseline written first (`seo/en.json`), reviewed, then translated. |
| **Slugs** | Whatever WordPress itself does, which is what the homepage shows: Latin scripts transliterated, non-Latin percent-encoded. `scripts/wpml/slugs.py` reproduces it and matches 35/37 of WordPress's own homepage slugs exactly (the other 2 were hand-set to `home`). |
| **Rev Slider** | Keep the English parent's alias in every language. `_g1` is copied verbatim; no per-language slider lookup. |
| **Image alt/title** | Not translated. `<img>` attributes are inside markup and never reach the translator. |

## Prerequisites

```
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
```

## Full run

```bash
CSV=all-pages-very-new.csv

# 1-2. inventory and extract the work units
python3 scripts/analyze_export.py $CSV
python3 scripts/extract.py       $CSV --out work

# 3. the English term glossary (321 terms)
python3 scripts/build_glossary.py $CSV --work work

# 4. REVIEW seo/en.json and work/glossary/en.json before spending anything

# 5. translate the glossary, then review work/glossary/<lang>.json
python3 scripts/build_glossary.py --work work --langs all

# 6. translate the pages (resumable; re-run to fill gaps)
python3 scripts/translate.py --work work --langs all --concurrency 4

# 7-9. assemble and validate
python3 scripts/assemble.py $CSV --work work --out import-pass1.csv
python3 scripts/validate.py import-pass1.csv --source $CSV --json work/report.json
```

`validate.py` exits non-zero on any failure. Do not import a file it rejects.

## Pilot first

German has a verified homepage translation to compare against, so start there:

```bash
python3 scripts/build_glossary.py --work work --langs de
python3 scripts/translate.py      --work work --langs de
python3 scripts/assemble.py $CSV  --work work --out de.csv --langs de
python3 scripts/validate.py de.csv --source $CSV
```

Import `de.csv` on staging and check: the language switcher links the group, a
child page (id 28) sits under its German parent, page 18's RankMath schema
survives, and the homepage slider still renders.

## Import, two passes

**Pass 1** — WP All Import, post type `page`:

* Unique identifier: **`import_key`**. This is what stops a re-run creating
  4,361 duplicate pages.
* Mode: create new / update existing.
* WPML add-on reads `_wpml_import_language_code`,
  `_wpml_import_source_language_code` and `_wpml_import_translation_group`.
* Leave `Parent` unmapped on this pass.

**Pass 2** — hierarchy. Re-export all pages, then:

```bash
python3 scripts/resolve_parents.py export-after-pass1.csv --source $CSV --out parents.csv
```

Import `parents.csv` as update-only, matched on `import_key`, mapping `Parent`
(48 rows per language, 1,776 in total).

## Scale

| | |
|---|---|
| Unique units after de-duplication | 4,655 (from 5,832 occurrences — 20% saved) |
| Source characters per language | 413,589 |
| Requests per language | 148 page batches + 7 glossary batches |
| Tokens per language | ~118K in, ~119K out |
| All 37 languages | ~4.4M in, ~4.4M out |

The cache in `work/translations/<lang>.json` is keyed on the SHA-1 of the source
string, so interrupting and re-running costs nothing. `--concurrency 4` runs
four languages at once.

## Testing without spending

`--engine mock` substitutes a deterministic fake translator through the whole
chain. Used to prove the pipeline end to end:

```bash
python3 scripts/translate.py --work work --langs de --engine mock
python3 scripts/assemble.py $CSV --work work --out de.csv --langs de
python3 scripts/validate.py de.csv --source $CSV      # exits 0
```

## What validate.py checks

Per generated row, against its English source:

* `ID` empty; group, translation id and all three WPML column pairs consistent;
  `_icl_lang_duplicate_of` empty; source language `en`.
* **Markup token sequence identical to English** — the check that proved the
  existing French homepage is correct.
* HTML entities unchanged (`&amp;` stays `&amp;`).
* Every serialized blob re-parses and is byte-canonical, so UTF-8 length
  prefixes are right.
* Taxonomy term counts unchanged.
* SEO title ≤60 and description ≤155 visible characters **in the target
  language**.
* Title and body actually differ from English, and the title contains the
  target script for non-Latin languages.
* Slug non-empty and `[a-z0-9%-]` only.

File-wide: no duplicate `import_key`, no duplicate (group, language) pair, no
duplicate slug within a language.

## English content bugs found on the way

Fix these before translating, or they get multiplied by 37:

* **Page 787 "Furniture Quality Control in Portugal"** contains the *Sport
  Items* body copy.
* **Page 794 "Apparel Quality Control in Portugal"** contains the *Hardware and
  Tools* body copy.
* **Page 649** is titled "Special Inspecrtions" (typo). It is a draft.
* **Page 9** has `_gglstmp_meta_canonical_tag = http://quality-assurance-agency-portugal`,
  which is not a valid URL. The pipeline blanks it rather than propagating it.
* Draft pages 648–653 duplicate the topics of published pages 690–704, so they
  compete for the same keywords. They ship as drafts, but consider deleting them.
