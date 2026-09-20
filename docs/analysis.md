# WPML page export — analysis and translation plan

Source file: `all-pages-very-new.csv` (2.08 MB, UTF-8, no BOM, `,` delimited,
RFC-4180 quoting, record terminator `LF`, `CRLF` **inside** content fields).

Reproduce every number below with:

```
python3 scripts/analyze_export.py all-pages-very-new.csv
```

---

## 1. What is in the file

| | |
|---|---|
| Columns | **107** |
| Data rows | **161** |
| English pages | **119** |
| Existing translation rows | **42** |
| Translation groups | **119** |
| Target languages | **37** (not 38 — see note) |
| Rows to generate | **4,361** |
| Final file | 4,522 rows |

**Language-count note.** The homepage group `533` holds 38 rows, but one of
them is the English original. The distinct non-English codes are 37:

```
ar bg da de el es fi fr ga he hi hu id is it ja ko lt lv ms nl no pl
pt-br pt-pt ro ru sk sl sq sr sv th tr uk vi zh-hans
```

If a 38th language is expected, it is missing from the homepage too and has to
be named explicitly before generation.

**Coverage today**

| Group | Page | Translations present |
|---|---|---|
| 533 | Home | 37 (complete) |
| 8 | About us | 1 (fr) |
| 17 | Inspection Services in Portugal | 1 (fr) |
| 25 | Vendor Audit in Portugal | 1 (fr) |
| 39 | Product Lab Testing & Certification | 1 (fr) |
| 759 | Nike Audit in Portugal | 1 (fr) |
| other 113 | — | 0 |

## 2. Duplicates

No duplicates that need fixing:

* `ID` — 161 unique.
* `Title` — 119 unique among English pages.
* `Slug` — 113 unique (6 English pages have an empty slug; WordPress derives
  it from the title on import).
* `Permalink` — unique.
* `Content` — no two non-empty bodies are identical.
* `import_key` — unique.

Two things that look like duplicates but are not:

* **38 English pages have an empty `Content`.** They are real pages whose body
  lives in the theme/page-builder or which are pure navigation hubs
  (`Industries`, `Blog`, `Careers`, the 9 `QMS … Derivated Audit` pages, the 12
  `… Products Testing Services` pages, the 6 drafts). Their `Title`,
  `_g1_subtitle`, SEO fields and taxonomy still need translating.
* **Duplicate column *names*.** `Title` appears at index 1 (post title) and 13
  (media title); `URL` at 12 and 18; `_wpml_import_language_code`,
  `_wpml_import_source_language_code` and `_wpml_import_translation_group`
  appear twice each (9/10/11 and 89/90/91). **Always address columns by index,
  never by name**, and keep both copies of the WPML triplet in sync.

**Near-duplicate content:** only 2 page pairs share >70% of their text
segments. But at segment level 6,117 text segments collapse to 4,329 unique —
**29% of all translatable text is repeated boilerplate** (CTAs, "Related Blog
Articles", "Certification" ×110, the standard footer block). A translation
memory keyed on the segment hash cuts ~29% of the cost and, more importantly,
guarantees the same English sentence always gets the same translation.

## 3. Volume

| | |
|---|---|
| English body words | 65,990 |
| × 37 languages | 2.44 M words |
| Translatable characters incl. titles/SEO/taxonomy | ~497 K |
| × 37 languages | ~18.4 M characters |
| Unique taxonomy terms | 5 categories + 280 tags + 276 relation tags |

Largest page is ~2,300 words; average 554.

## 4. The structure a translation row must have

Learned by diffing all 37 homepage translations against the English row. This
is the contract — get it wrong and WPML silently creates orphan pages.

| Column | Value on a translation row |
|---|---|
| 0 `ID` | **empty** (WP All Import then creates a new post) |
| 7 `WPML Translation ID` | **= the English post ID**, identical across the group |
| 8 `WPML Language Code` | target code, e.g. `de` |
| 9 `_wpml_import_language_code` | target code (same as 8) |
| 10 `_wpml_import_source_language_code` | `en` (empty on the English row) |
| 11 `_wpml_import_translation_group` | **= the English post ID** — `533` for the homepage |
| 89 / 90 / 91 | exact duplicates of 9 / 10 / 11 |
| 84 `_icl_lang_duplicate_of` | **must stay empty** — a value here makes WPML treat the page as a *duplicate*, not a *translation* |
| 85 `_last_translation_edit_mode` | `native-editor` |
| 86 `import_key` | `<english_id>-<lang>`, e.g. `8-de` — the pattern the 5 existing FR pages already use |

`import_key` is the most valuable field in the file: it is unique, stable and
derivable. Use it as WP All Import's *unique identifier* so a re-run **updates**
rows instead of creating 4,361 duplicate pages.

## 5. Fields to translate

Full machine-readable table: `scripts/field_rules.py` (all 107 columns
classified). Summary:

**Translate (20 columns)**

`Title`, `Content`, `Excerpt`, media `Title`/`Caption`/`Description`/`Alt Text`,
`_g1_subtitle`, the three `_g_feedback_shortcode_*` form definitions,
`rank_math_title`, `rank_math_description`, `rank_math_facebook_title`,
`rank_math_facebook_description`, `rank_math_focus_keyword`, and the ACF text
values `rep_office_address`, `city1`, `city2`, `list_cities`.

**Translate as pipe-delimited term lists (3 columns)**

`Categories`, `Tags`, `Relation Tags`.

**Translate inside PHP-serialised blobs (5 columns)**

`_g1`, `rank_math_schema_Service`, and the three
`_g_feedback_shortcode_atts_*`.

**Derive per language (9)** · `WPML Language Code`, both
`_wpml_import_language_code`, `_wpml_word_count`, `import_key`, `Slug`,
`Parent`, `Parent Slug`, `Post Modified Date`.

**Constant (4)** · both `_wpml_import_source_language_code` = `en`,
`Translation Priorities` = `Optional`, `_last_translation_edit_mode` =
`native-editor`.

**Blank (7)** · `ID`, `Permalink`, `rank_math_analytic_object_id`,
`_gglstmp_meta_canonical_tag`, `_jetpack_related_posts_cache`, `_alp_processed`,
`_icl_lang_duplicate_of`.

**Copy verbatim from English (59)** · everything else — ACF *field keys*
(`_country`, `_phone`, `_city1` …, which are `field_69aafcab3e7c9`-style
pointers and would break the page if touched), glossary/CMTT flags, author
columns, template, order, comment/ping status, media ids, CSS.

### SEO gap worth knowing about

RankMath is barely filled in on the English side:

| Field | English pages with a value |
|---|---|
| `rank_math_title` | 8 / 119 |
| `rank_math_description` | 8 / 119 |
| `rank_math_facebook_title` | 5 / 119 |
| `rank_math_facebook_description` | 5 / 119 |
| `rank_math_focus_keyword` | 1 / 119 — and its value is `1788605996`, a stray timestamp, not a keyword |

So "translate the SEO fields" gives you almost nothing. The homepage
translators worked around this by *writing* SEO fields that the English row
does not have (the English `rank_math_schema_Service` is empty; all 37
translations have one). Decide between:

* **A — mirror English.** Empty stays empty. Safe, fast, but 111 pages ship
  with no meta title/description in any language.
* **B — generate English first**, review it, then translate. Best SEO outcome
  and the English site improves too.
* **C — generate directly per language** from the page title + body, with the
  focus keyword *localised* (`inspection portugal` → `portugal inspektion`,
  not a word-for-word translation), which is what the homepage rows do.

Recommendation: **B**, with C as the fallback for pages you do not want to
hand-review. Either way the generated strings must respect RankMath's limits —
~60 visible characters for the title, ~155 for the description — measured in
the target language, which is where machine translation usually overflows.

## 6. Structured content that must survive intact

The 37 homepage translations prove the rule: **the markup is byte-identical
across all languages; only the text between the markup changes.** Verified —
the English and French homepage bodies contain exactly the same 184 shortcode
tokens in exactly the same order.

### 6.1 Shortcodes (~2,600 occurrences, 36 distinct)

```
[section background_repeat="repeat" background_position="center top" …]
[one_third valign="top" animation="none"] … [/one_third]
[button size="medium" link="/contact" style="solid" icon="question"]<strong>…</strong>[/button]
[icon name="check-circle" size="medium" text_color="#b90e13"][/icon]
[numbers start="0" stop="48" icon="time" suffix="H"] … [/numbers]
[contact-form-7 id="893" title="Bottom Pages Contact Form"]
[related_pages max="6" template="one_third" effect="grayscale" hide="summary,author"]
[Country] [page_tags] [glossary] [smartslider3 alias="audits"] [CP_CALCULATED_FIELDS id="6"]
```

Rules:

* Never translate a shortcode **name** or **attribute value**. `icon="check"`,
  `name="check-circle"`, `style="solid"`, `template="one_third"`,
  `hide="summary,author"` are theme identifiers. `link="/contact"` stays as-is
  — WPML rewrites internal links at render time, and the homepage FR row
  confirms it was left untouched.
* `[contact-form-7 id="893" title="Bottom Pages Contact Form"]` — the `title`
  attribute is an internal form label, not visible copy. Left untranslated in
  every existing translation. Keep it.
* `[Country]` is a placeholder that renders "Portugal". Keep the literal token.
* Text **between** opening and closing shortcodes is the translatable part,
  including text that sits inside an `<h2>` that also contains an inline
  `[icon …][/icon]`.

### 6.2 HTML

`<li>` ×3054, `<strong>` ×2005, `<ul>`, `<h2>`–`<h5>`, `<p>`, `<img>`, `<a>`,
`<table>`. Tags, classes, `style="text-align: center;"`, `href`, `src`,
`width`, `height` all stay. `&amp;` stays encoded. In the existing
translations even `<img title>` and `<img alt>` were left in English — worth
changing (alt text is an SEO asset), but it is a deliberate choice, not the
default.

### 6.3 PHP-serialised metadata — the real trap

`rank_math_schema_Service`, `_g1`, `_g_feedback_shortcode_atts_*`, `os_meta`,
`copied_media_ids`, `referenced_media_ids`, `_g1_gmaps_metabox`,
`rank_math_og_content_image`, `_jetpack_related_posts_cache` are PHP
`serialize()` strings:

```
a:7:{s:8:"metadata";a:5:{…}s:5:"@type";s:7:"Service";
     s:4:"name";s:42:"Services d'inspection qualité au Portugal";…}
```

`s:42:` is a **byte** count, not a character count. `"Services d'inspection
qualité au Portugal"` is 41 characters but 42 bytes because `é` is two bytes in
UTF-8. Get this wrong by one and PHP's `unserialize()` returns `false`, the
meta silently evaporates, and the page loses its schema. The existing FR/DE
rows have the counts right — whatever produces the new rows must too.

So: never regex-replace inside these fields. Unserialise → translate only the
whitelisted string values → re-serialise with `len(value.encode('utf-8'))`.

Whitelist per field:

| Field | Translate | Leave alone |
|---|---|---|
| `rank_math_schema_Service` | `name`, `description`, `serviceType` | `metadata.*`, `@type`, `shortcode`, `offers`, `image`, `%post_thumbnail%` |
| `_g1` | `single_element_slider` *only if* a per-language slider exists | all other keys |
| `_g_feedback_shortcode_atts_*` | `subject`, `submit_button_text`, `customThankyouHeading`, `customThankyouMessage` | `to`, `id`, `widget`, `block_template`, `jetpackCRM` |
| `os_meta`, `_g1_gmaps_metabox`, `*_media_ids`, `rank_math_og_content_image` | nothing | everything |

### 6.4 Revolution Slider aliases

The homepage `_g1` points at a **different slider per language**:
`revslider_home` → `revslider_home-german`, `revslider_home-french`,
`revslider_home-arabic` … all 37 exist in WordPress already. One other English
page uses `revslider_production-monitoring-service-…` and has **no**
per-language variants.

Rule: only swap the alias when the language-specific slider actually exists in
WordPress; otherwise keep the English alias, or the page renders an empty
slider. This needs a lookup table exported from the site
(`wp revslider list` or the `wp_revslider_sliders` table) — it cannot be
inferred from the CSV. Note the naming is *language names*, irregular
(`-pt-brazil`, `-portugese`, `-ukranian`, `-chinese`), so it must be a literal
map, not an algorithm.

### 6.5 Taxonomy terms

`Categories` and `Tags` are pipe-delimited term names. Translated cleanly on
the homepage (4 categories per language). But the homepage **tag** lists are
dirty: French carries 8 French tags *plus* the 10 original English ones (18
total), Arabic 17. That happened because untranslated English terms stayed
attached. For the new rows, emit **only** the translated terms — cleaner, and
it stops 280 English tags leaking into 37 language sitemaps.

Also: translate each of the 280 tags **once** into a term glossary, not once
per page. 5 + 280 + 276 terms × 37 languages = ~21 K term translations, which
is a single cheap batch job, and it guarantees the same term never gets two
spellings.

`Translation Priorities` is a WPML taxonomy. Its existing values are already
inconsistent (`Optional`, `Facultatif`, `Facultatif|Facultatif`,
`Opcional|Opcional`, `Valfri|Valfri`). Set every new row to the literal
`Optional` so no junk terms are created.

### 6.6 Page hierarchy — the one thing with no reference example

**48 of the 119 English pages have a parent** (16 under `Vendor Audit`, 11
under `Inspection Services`, 11 under `Product Lab Testing`, 5 under `About
us`, 5 under `Industries`). Every page that already has a translation is
top-level, so the export shows no worked example of a translated child.

`Parent` is a numeric post ID that will not exist until the import runs, and a
German child must point at the **German** parent, not the English one.
Solution:

1. Emit new rows with `Parent` / `Parent Slug` **empty**.
2. Import pass 1 creates all 4,361 pages flat and returns the new IDs.
3. Export the resulting `import_key → post ID` map.
4. Import pass 2 (update-only, matched on `import_key`) sets `Parent` from the
   map: parent of `28-de` = the new ID of `25-de`.

Ordering the rows parents-first inside each language and letting WP All Import
match `Parent Slug` also works, but it is fragile when slugs collide — the
two-pass map is deterministic.

### 6.7 Slugs

Existing translated slugs are WordPress's own output: ASCII transliteration for
Latin scripts (`pradzia`, `kezdolap`), **percent-encoded UTF-8** for non-Latin
(`%d0%bd%d0%b0%d1%87%d0%b0%d0%bb%d0%be-3` = `начало-3`), plus `-2`/`-3`
collision suffixes.

For 4,361 new pages, generate slugs deliberately instead of letting WordPress
improvise:

* Latin-script languages: transliterate the translated title to ASCII,
  lowercase, hyphenate, truncate to ~60 chars.
* Non-Latin scripts: either romanise the translated title, or reuse the English
  slug. Both are better for SEO and for link-sharing than percent-encoding.
* De-duplicate **within each language** before writing the file, so WordPress
  never has to append `-2`.

## 7. Automation plan

Ten steps. Steps 1–3 and 5–10 are fully automatic; step 4 is the only place a
human decision is needed, and it is three yes/no answers.

**Step 1 — Freeze the contract.**
Parse the CSV by index, assert 107 columns, load `scripts/field_rules.py`.
Keep the 161 original rows **byte-identical** by copying their raw source lines
rather than re-serialising them; only the appended rows are newly written.
Output: validated in-memory model + the unchanged original block.

**Step 2 — Extract the work units.**
For each of the 119 English pages, split `Content` into an ordered list of
translatable segments with the markup between them held as opaque
placeholders, and pull the plain fields (`Title`, `_g1_subtitle`, SEO, ACF) and
the serialised-field string values. Output: `work/segments.jsonl`, one record
per (page, field, segment) with a stable hash id.

**Step 3 — Build the term glossary.**
Collect the 5 categories, 280 tags, 276 relation tags and the recurring brand
terms (`Portugal Quality Control`, service names, city names). Output:
`work/glossary.en.json`.

**Step 4 — Three decisions.** *(decided — see `docs/pipeline.md`)*
1. SEO: **option B**. English baseline written first in `seo/en.json`, reviewed,
   then translated.
2. Slugs: **whatever WordPress does**, as the homepage shows — Latin scripts
   transliterated, non-Latin percent-encoded.
3. Revolution Slider: **keep the English parent's alias** in every language.

Also decided: `<img>` `alt` and `title` are **not** translated.

**Step 5 — Translate the glossary, 37 languages.**
One batch job, ~21 K short strings. Human-reviewable in a single spreadsheet —
this is the highest-leverage review point in the whole project, because every
page inherits it. Output: `work/glossary.<lang>.json`.

**Step 6 — Translate the segments, 37 languages.**
Batch by page, with the glossary injected into the prompt and a
content-hash cache so each of the 4,329 unique segments is translated once per
language (29% saving). Model returns segments only; markup is never sent, so it
cannot be mangled. Output: `work/segments.<lang>.jsonl`.

**Step 7 — Validate every translated unit** *(automatic, hard gate)*
* segment count in == segment count out;
* re-assembled body has the identical shortcode token sequence as English
  (the check that proved the homepage is correct);
* HTML tag sequence identical, `&amp;`-style entities preserved;
* no untranslated-language leakage on long segments;
* SEO title ≤60 and description ≤155 visible characters;
* serialised blobs round-trip through `unserialize()` with byte-correct
  lengths.
  Anything that fails is re-translated, not shipped. Output: `work/report.json`.

**Step 8 — Assemble the 4,361 rows.**
Apply `field_rules.py`: copy 59 columns, write the 20 translated, 3 term-list
and 5 serialised ones, derive the 9, set the 4 constants, blank the 7. Set
`import_key = <en_id>-<lang>`, group = English ID, source = `en`, leave `ID`,
`Parent` and `Parent Slug` empty. Generate per-language unique slugs.

**Step 9 — Write the import file.**
Original 161 rows verbatim, then the new rows sorted by (English ID, language).
UTF-8, no BOM, `LF` record terminator, `CRLF` preserved inside content. Then
re-run `scripts/analyze_export.py` on the output: it must report 4,522 rows,
107 columns, 119 groups of 38, zero duplicate `import_key`.

**Step 10 — Import, in two passes.**
Pass 1: WP All Import, post type `page`, unique identifier `import_key`,
"create new / update existing", WPML add-on reading
`_wpml_import_language_code` / `_wpml_import_source_language_code` /
`_wpml_import_translation_group`. Pass 2: update-only run that fills `Parent`
from the `import_key → post ID` map (§6.6).

**Before the full run:** do one language (`de`, which already has a verified
homepage to diff against) × 5 pages including one child page and one
empty-content page, on staging. Confirm the language switcher links the group,
the parent resolves, the schema meta survives, and the slider renders. Then
scale to 37.

## 8. Risks

| Risk | Mitigation |
|---|---|
| Serialised meta silently dropped (byte-length bug) | unserialise/re-serialise, never regex; validate in step 7 |
| 4,361 duplicate pages on a re-run | `import_key` as the unique identifier |
| Child pages orphaned at the site root | two-pass import (§6.6) |
| WPML treats pages as duplicates, not translations | `_icl_lang_duplicate_of` stays empty; all three WPML columns present in both copies |
| Broken layout from a mangled shortcode | markup never reaches the model; token-sequence equality check |
| Empty sliders in 36 languages | alias map, or keep the English alias |
| SEO titles overflowing in German/Finnish | length check in the target language, regenerate on failure |
| 280 English tags leaking into every language | term glossary; emit translated terms only |
| Export/import round-trip corruption | original rows copied byte-identical; re-run the analyzer on the output |
