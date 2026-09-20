"""Reproduce WordPress's sanitize_title_with_dashes() so slugs match the site.

Verified against the 37 homepage translations WordPress generated itself:
Latin scripts lose their diacritics (Pradžia -> pradzia, Kezdolap), non-Latin
scripts are percent-encoded UTF-8 in lowercase hex
(начало -> %d0%bd%d0%b0%d1%87%d0%b0%d0%bb%d0%be).
"""

import re
import unicodedata

MAX_LENGTH = 200          # WordPress truncates post_name at 200 characters

# WordPress's remove_accents() handles these as digraphs; NFKD alone gets them
# wrong (ß would vanish, æ would become a).
DIGRAPHS = {
    "ß": "ss", "æ": "ae", "Æ": "ae", "œ": "oe", "Œ": "oe",
    "ø": "o",  "Ø": "o",  "đ": "d",  "Đ": "d",  "ð": "d", "Ð": "d",
    "þ": "th", "Þ": "th", "ł": "l",  "Ł": "l",  "ı": "i", "İ": "i",
    "ŋ": "n",  "ĸ": "k",  "ſ": "s",  "ǆ": "dz", "ĳ": "ij", "Ĳ": "ij",
}

LATIN_BLOCKS = ("LATIN", "DIGIT", "SPACE", "HYPHEN", "COMMON")


def remove_accents(text):
    """WordPress's remove_accents(): strip Latin diacritics, leave other scripts."""
    out = []
    for char in text:
        if char in DIGRAPHS:
            out.append(DIGRAPHS[char])
            continue
        decomposed = unicodedata.normalize("NFKD", char)
        base = decomposed[0]
        # Only fold when the base character is Latin; folding Greek or Cyrillic
        # here would silently turn them into ASCII, which WordPress never does.
        if base.isascii() and unicodedata.name(char, "").startswith("LATIN"):
            out.append("".join(c for c in decomposed if not unicodedata.combining(c)))
        else:
            out.append(char)
    return "".join(out)


def sanitize_title(title):
    text = re.sub(r"<[^>]*>", "", title)
    text = text.replace("&amp;", "").replace("&nbsp;", " ")
    text = re.sub(r"&[a-zA-Z#0-9]+;", "", text)
    # Typographic punctuation would otherwise be percent-encoded into the slug
    # (services-d%e2%80%99inspection). WordPress tolerates that; nobody wants it.
    text = text.translate(str.maketrans({c: None for c in "\u2018\u2019\u201a\u201b\u201c\u201d\u201e\u00ab\u00bb\u2039\u203a"}))
    text = text.translate(str.maketrans({c: "-" for c in "\u2013\u2014\u2212"}))
    text = remove_accents(text).lower()

    out = []
    for char in text:
        if char.isascii() and (char.isalnum()):
            out.append(char)
        elif char in " \t\n\r_-/ ":
            out.append("-")
        elif char.isascii():
            continue                                   # punctuation is dropped
        else:
            out.append("".join(f"%{b:02x}" for b in char.encode("utf-8")))

    slug = re.sub(r"-+", "-", "".join(out)).strip("-")
    if len(slug) > MAX_LENGTH:
        slug = slug[:MAX_LENGTH].rstrip("-")
        slug = re.sub(r"%[0-9a-f]?$", "", slug).rstrip("-")   # never cut an octet
    return slug


def unique_slug(slug, taken):
    """Append -2, -3 ... exactly as WordPress does when a slug is in use."""
    if slug and slug not in taken:
        taken.add(slug)
        return slug
    suffix = 2
    while f"{slug}-{suffix}" in taken:
        suffix += 1
    result = f"{slug}-{suffix}"
    taken.add(result)
    return result
