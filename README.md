# WPML translation pipeline — portugalqualitycontrol.com

Translating 119 English WordPress pages into 37 languages and re-importing
them through WPML + WP All Import.

* `docs/analysis.md` — analysis of the export and the 10-step automation plan.
* `scripts/analyze_export.py` — inventory/validation pass over any export CSV.
  Run it on the source file and again on the generated import file.
* `scripts/field_rules.py` — per-column handling rules for all 107 columns.

```
python3 scripts/analyze_export.py all-pages-very-new.csv
python3 scripts/field_rules.py
```

CSV exports are not committed; keep them out of the repo.
