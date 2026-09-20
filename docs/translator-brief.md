# Translator brief

You are translating the website of **Portugal Quality Control**, an independent
quality-inspection company operating in Portugal, from English into one target
language. The audience is B2B: importers, buyers, sourcing managers and
manufacturers who buy or produce goods in Portugal.

## How the work is exchanged

Units are numbered lines of `index<TAB>English text`. You return
`index<TAB>translation`, same index, one per line, nothing else.

```
python3 scripts/units_io.py list --work work --from 0 --count 400 --max-chars 7000
python3 scripts/units_io.py add  --work work --lang de --tsv batch.tsv
python3 scripts/units_io.py todo --work work --lang de
```

Write each batch to a file under `/tmp` and ingest it. Never edit
`work/translations/*.json` by hand — `add` writes it and keys it correctly.

## Rules, in priority order

1. **One line out for every line in.** Same index. Never merge, split, reorder,
   drop or add lines. A missing index means that string silently ships in
   English.
2. **Literal `\n`** is a paragraph break inside a unit. Reproduce it exactly as
   the two characters `\` and `n` — do not turn it into a real newline, and do
   not drop it. A real newline inside your output breaks the file.
3. **Never translate markup or placeholders.** If a unit contains something like
   `{{City1}}`, `%seo_title%`, `[icon ...]` or `<strong>`, copy it character for
   character. (Most markup was stripped before you see it, but fragments remain.)
4. **HTML entities stay encoded.** `&amp;` stays `&amp;` — never `&`, never the
   word "and". Same for `&nbsp;`, `&#8217;` and friends.
5. **Never translate these:**
   - the company name **Portugal Quality Control** (and the bracketed email
     subject `[Portugal Quality Control] ...` keeps the brackets and the name)
   - place names: Portugal, Lisbon, Porto, Braga, Aveiro, Coimbra, Leiria,
     Setúbal, Guimarães, Viana do Castelo, Faro, Sines, Leixões, Marinha Grande
   - standards and schemes: ISO, IATF, SA8000, BSCI, SMETA, Sedex, CTPAT, GMP,
     AQL, REACH, RoHS, EMC, LVD, CE, EN 71, NDT, CMM, DUPRO, PSI, ANSI, ASQC,
     MIL-STD, amfori, CPR
   - retailer names: Nike, Costco, Walmart, Disney, Tesco, Target
   Decline place names grammatically where your language requires it, but never
   substitute a local exonym for the company name.
6. **Register.** B2B service marketing: direct, professional, concrete. Use the
   formal address form where your language distinguishes one (Sie, vous, usted,
   Vous). Address the reader as a business buyer, not a consumer.
7. **Consistency beats variety.** The same English term must get the same
   translation every time it appears. Recurring terms: quality inspection,
   quality control, factory audit, vendor audit, supplier evaluation,
   pre-shipment inspection, during production inspection, initial production
   inspection, production monitoring, defect sorting, container loading
   inspection, cargo survey, full inspection, dimensional inspection, product
   testing, social audit, supply chain, importer, buyer, supplier, vendor,
   inspector, auditor, defect, compliance, certification, checklist,
   third-party inspection, quality assurance, corrective action.
8. **Length.** Keep roughly the source length. Do not add explanations, do not
   expand abbreviations, do not omit detail.
9. **Punctuation.** Preserve leading and trailing punctuation, including a
   trailing colon, question mark or exclamation mark. Fragments that end
   mid-sentence stay fragments — many units are pieces of a sentence split by
   markup, so translate them as the fragment they are, not as a full sentence.

## Field-specific rules

Some units are SEO fields. You can tell from their content, and the index list
follows the page order, but the binding constraints are:

- **SEO titles** (short, often with a `|` separator): at most **60 characters**
  in your language. Rewrite rather than translate literally if a direct
  translation overflows. Keep the `|` separator.
- **SEO meta descriptions** (one or two sentences, marketing tone): at most
  **155 characters** in your language. Rewrite to fit; never truncate
  mid-sentence.
- **Focus keywords** (lowercase, 2–5 words, always containing "portugal"):
  **do not translate literally**. Give the phrase a native speaker would
  actually type into Google for this service in Portugal. Keep it lowercase and
  keep the word for Portugal in it.
- **Taxonomy terms** (category and tag names): short noun phrases, no sentence
  punctuation, no trailing period.

## Do not

- Do not run any `git` command. The parent session commits.
- Do not touch any language other than the one you were assigned.
- Do not edit files outside `work/translations/<your lang>.json` (via `add`).
- Do not "fix" the English. Typos, duplicated content and odd phrasing in the
  source are known and out of scope — translate what is there.

## Finish

Run `todo` for your language and range. Every index in your range must be
present. Report the final count.
