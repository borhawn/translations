"""Split WordPress content into translatable text and untouchable markup.

The contract proven by the existing homepage translations: markup is
byte-identical across all 38 languages, only the text between it changes. This
module enforces that mechanically — the markup never reaches the translator, so
it cannot come back mangled.

    tokens = tokenize(content)
    units  = translatable(tokens)        # what the model sees
    body   = rebuild(tokens, {uid: translated})
"""

import hashlib
import re

# A shortcode, an HTML tag, an ACF merge tag ({{City1}}) or a RankMath
# variable (%seo_title%). Order matters: shortcodes first, because a shortcode
# may sit inside an <h2> and must stay opaque either way.
MARKUP_RE = re.compile(r"\[/?[^\[\]]*\]|<[^<>]*>|\{\{[^{}]*\}\}|%[a-z_]+%")

# A value that is nothing but a placeholder is configuration, not copy.
PLACEHOLDER_ONLY_RE = re.compile(r"^\s*(?:\{\{[^{}]*\}\}|%[a-z_]+%)\s*$")


def is_placeholder(text):
    return bool(PLACEHOLDER_ONLY_RE.match(text))

# Text that carries no words (whitespace, bullets, stray punctuation) is never
# sent for translation.
HAS_WORD_RE = re.compile(r"[^\W\d_]", re.UNICODE)

# Leading/trailing whitespace is part of the layout, not of the sentence.
EDGE_WS_RE = re.compile(r"^(\s*)(.*?)(\s*)$", re.DOTALL)


class Token:
    __slots__ = ("kind", "text", "prefix", "core", "suffix", "uid")

    def __init__(self, kind, text):
        self.kind = kind                     # "markup" | "text"
        self.text = text
        self.prefix = self.core = self.suffix = ""
        self.uid = None
        if kind == "text":
            self.prefix, self.core, self.suffix = EDGE_WS_RE.match(text).groups()
            if HAS_WORD_RE.search(self.core):
                self.uid = segment_id(self.core)

    @property
    def translatable(self):
        return self.uid is not None

    def render(self, replacement=None):
        if self.kind == "markup" or replacement is None:
            return self.text
        return f"{self.prefix}{replacement}{self.suffix}"


def segment_id(core):
    """Stable id for a piece of source text, so identical text is translated once."""
    return hashlib.sha1(core.encode("utf-8")).hexdigest()[:16]


def tokenize(content):
    tokens, cursor = [], 0
    for match in MARKUP_RE.finditer(content):
        if match.start() > cursor:
            tokens.append(Token("text", content[cursor:match.start()]))
        tokens.append(Token("markup", match.group(0)))
        cursor = match.end()
    if cursor < len(content):
        tokens.append(Token("text", content[cursor:]))
    return tokens


def translatable(tokens):
    """Ordered, de-duplicated {uid: source text} for the tokens that need work."""
    units = {}
    for token in tokens:
        if token.translatable:
            units.setdefault(token.uid, token.core)
    return units


def rebuild(tokens, translations):
    """Reassemble, substituting translations by uid. Missing uids keep English."""
    return "".join(
        token.render(translations.get(token.uid)) if token.translatable else token.text
        for token in tokens
    )


def markup_signature(content):
    """The sequence of markup tokens — must be identical in every language."""
    return MARKUP_RE.findall(content)


def entity_signature(content):
    """HTML entities must survive translation unchanged (&amp; stays &amp;)."""
    return sorted(re.findall(r"&[a-zA-Z#0-9]+;", content))


def plain_words(content):
    """Word count the way WPML's _wpml_word_count does it: visible text only."""
    text = MARKUP_RE.sub(" ", content)
    return len(re.sub(r"\s+", " ", text).strip().split())
