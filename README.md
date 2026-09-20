# WPML translation pipeline — portugalqualitycontrol.com

Translates 119 English WordPress pages into 37 languages and produces a CSV that
imports back through WPML + WP All Import.

Markup never reaches the translator. Page bodies are split into text segments
with every shortcode, HTML tag, `{{merge_tag}}` and `%variable%` held back as an
opaque token, so the 2,600 shortcodes and 5,700 HTML tags come back
byte-identical by construction — then `validate.py` proves it before anything is
imported.

## Documents

* `docs/analysis.md` — what is in the export and why each column is handled the way it is.
* `docs/pipeline.md` — how to run it, the two-pass import, what gets validated.
* `seo/en.json` — the reviewed English SEO baseline for all 119 pages.

## Scripts

| | |
|---|---|
| `analyze_export.py` | inventory/validation pass over any export CSV |
| `extract.py` | English pages → translation work units |
| `build_glossary.py` | 321-term glossary, English then per language |
| `translate.py` | the translation pass; resumable, cached, `--engine mock` for dry runs |
| `assemble.py` | work units + originals → the import CSV |
| `validate.py` | the hard gate; exits non-zero on any failure |
| `resolve_parents.py` | pass-2 file that re-parents the 48 child pages |
| `field_rules.py` | per-column handling rules for all 107 columns |
| `wpml/` | shared library: CSV fidelity, markup tokeniser, PHP serializer, slugs, prompts |

## Quick start

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
CSV=all-pages-very-new.csv

python3 scripts/extract.py        $CSV --out work
python3 scripts/build_glossary.py $CSV --work work
python3 scripts/build_glossary.py --work work --langs de
python3 scripts/translate.py      --work work --langs de
python3 scripts/assemble.py $CSV  --work work --out de.csv --langs de
python3 scripts/validate.py de.csv --source $CSV
```

CSV exports and the `work/` cache are not committed.
