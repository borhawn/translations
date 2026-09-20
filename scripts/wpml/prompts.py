"""Prompt construction for the translation pass."""

from . import langs

BRAND_TERMS = [
    "Portugal Quality Control",   # the company name, never translated
    "Portugal", "Lisbon", "Porto", "Braga", "Aveiro", "Coimbra", "Leiria",
    "Setúbal", "Guimarães", "Viana do Castelo", "Faro", "Sines", "Leixões",
    "Marinha Grande",
    "ISO", "IATF", "SA8000", "BSCI", "SMETA", "Sedex", "CTPAT", "GMP", "AQL",
    "REACH", "RoHS", "EMC", "LVD", "CE", "EN 71", "NDT", "CMM", "DUPRO", "PSI",
    "ANSI", "ASQC", "MIL-STD", "amfori",
    "Nike", "Costco", "Walmart", "Disney", "Tesco", "Target",
]

SYSTEM = """You translate marketing copy for a quality-inspection company that \
operates in Portugal. You translate from English into {language} ({code}).

Rules, in priority order:

1. Return a translation for every id you are given, and nothing else. Never \
merge, split, reorder, drop or add items.
2. The text you receive is plain prose. It contains NO HTML and NO shortcodes — \
those were removed before you saw them. If you find something that looks like \
markup, a {{{{placeholder}}}} or a %variable%, reproduce it character for \
character.
3. Keep HTML entities exactly as written: &amp; stays &amp;, never & or "and".
4. Never translate these: {brand}. Company name, place names, standards and \
retailer names stay in their original form. Decline place names grammatically \
where {language} requires it, but do not substitute a local exonym for the \
company name.
5. Match the register of B2B service marketing in {language}: direct, \
professional, addressing the reader as a business buyer. Use the formal \
address form where {language} distinguishes one.
6. Use the supplied glossary for every term it covers. Consistency across pages \
matters more than variety.
7. Preserve the leading and trailing punctuation of each item, including a \
trailing colon, question mark or exclamation mark.
8. Keep the text roughly the same length. Do not add explanations, do not \
expand abbreviations, do not omit detail.

Output format: one line per item, exactly `id<TAB>translation`. No preamble, no \
numbering, no code fences, no blank lines."""

KIND_NOTES = {
    "seo_title": "These are SEO page titles. Keep each under 60 characters in "
                 "{language} — rewrite rather than translate literally if a "
                 "direct translation would overflow. Keep the pipe separator.",
    "seo_description": "These are SEO meta descriptions. Keep each under 155 "
                       "characters in {language}. Rewrite to fit rather than "
                       "truncating mid-sentence.",
    "og_title": "These are social share titles. Keep each under 60 characters.",
    "og_description": "These are social share descriptions. Keep under 155 "
                      "characters.",
    "focus_keyword": "These are SEO focus keywords. Do NOT translate literally "
                     "— give the phrase a {language} speaker would actually "
                     "type into Google for this service in Portugal. Lowercase, "
                     "2-5 words, keep the word for Portugal in it.",
    "term": "These are taxonomy term names (categories and tags). Translate as "
            "short noun phrases, no sentence punctuation, no trailing period.",
    "media": "These are media library titles and alt texts.",
    "body":  "These are fragments of page body copy. A fragment may be a "
             "heading, a sentence, a list item or a button label.",
    "field": "These are short page fields: titles, subtitles and form labels.",
}


def system_prompt(code):
    return SYSTEM.format(language=langs.name(code), code=code,
                         brand=", ".join(BRAND_TERMS))


def user_prompt(code, kind, items, glossary):
    """items: [(id, text)]  glossary: {english: translated}"""
    lines = []
    note = KIND_NOTES.get(kind)
    if note:
        lines.append(note.format(language=langs.name(code)))
        lines.append("")
    relevant = {en: tr for en, tr in glossary.items()
                if any(en.lower() in text.lower() for _, text in items)}
    if relevant:
        lines.append("Glossary — use these exact renderings:")
        for en, tr in sorted(relevant.items()):
            lines.append(f"  {en} = {tr}")
        lines.append("")
    lines.append(f"Translate these {len(items)} items into {langs.name(code)}:")
    lines.append("")
    for uid, text in items:
        lines.append(f"{uid}\t{text}")
    return "\n".join(lines)


def parse_response(text, expected_ids):
    """Parse `id<TAB>translation` lines. Returns (translations, problems)."""
    out, problems = {}, []
    for line in text.splitlines():
        if not line.strip() or "\t" not in line:
            continue
        uid, _, translation = line.partition("\t")
        uid = uid.strip()
        if uid in expected_ids:
            out[uid] = translation.strip()
    missing = [i for i in expected_ids if i not in out]
    if missing:
        problems.append(f"{len(missing)} items missing from the response")
    return out, problems
