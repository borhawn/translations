"""The 37 target languages, taken from the completed homepage group (533)."""

# code -> (English name, endonym, script family)
LANGUAGES = {
    "ar":      ("Arabic",              "العربية",     "arabic"),
    "bg":      ("Bulgarian",           "български",   "cyrillic"),
    "da":      ("Danish",              "dansk",       "latin"),
    "de":      ("German",              "Deutsch",     "latin"),
    "el":      ("Greek",               "Ελληνικά",    "greek"),
    "es":      ("Spanish",             "español",     "latin"),
    "fi":      ("Finnish",             "suomi",       "latin"),
    "fr":      ("French",              "français",    "latin"),
    "ga":      ("Irish",               "Gaeilge",     "latin"),
    "he":      ("Hebrew",              "עברית",       "hebrew"),
    "hi":      ("Hindi",               "हिन्दी",        "devanagari"),
    "hu":      ("Hungarian",           "magyar",      "latin"),
    "id":      ("Indonesian",          "Indonesia",   "latin"),
    "is":      ("Icelandic",           "íslenska",    "latin"),
    "it":      ("Italian",             "italiano",    "latin"),
    "ja":      ("Japanese",            "日本語",       "japanese"),
    "ko":      ("Korean",              "한국어",       "korean"),
    "lt":      ("Lithuanian",          "lietuvių",    "latin"),
    "lv":      ("Latvian",             "latviešu",    "latin"),
    "ms":      ("Malay",               "Melayu",      "latin"),
    "nl":      ("Dutch",               "Nederlands",  "latin"),
    "no":      ("Norwegian",           "norsk",       "latin"),
    "pl":      ("Polish",              "polski",      "latin"),
    "pt-br":   ("Brazilian Portuguese", "português do Brasil", "latin"),
    "pt-pt":   ("European Portuguese",  "português de Portugal", "latin"),
    "ro":      ("Romanian",            "română",      "latin"),
    "ru":      ("Russian",             "русский",     "cyrillic"),
    "sk":      ("Slovak",              "slovenčina",  "latin"),
    "sl":      ("Slovenian",           "slovenščina", "latin"),
    "sq":      ("Albanian",            "shqip",       "latin"),
    "sr":      ("Serbian",             "srpski",      "latin"),
    "sv":      ("Swedish",             "svenska",     "latin"),
    "th":      ("Thai",                "ไทย",         "thai"),
    "tr":      ("Turkish",             "Türkçe",      "latin"),
    "uk":      ("Ukrainian",           "українська",  "cyrillic"),
    "vi":      ("Vietnamese",          "Tiếng Việt",  "latin"),
    "zh-hans": ("Simplified Chinese",  "简体中文",     "chinese"),
}

CODES = list(LANGUAGES)

# Languages whose scripts count characters, not words, for SEO length budgets.
CJK = {"ja", "ko", "zh-hans", "th"}

# Right-to-left languages: the translated copy must not reorder Latin brand
# names, and RankMath length budgets are measured the same way.
RTL = {"ar", "he"}


def name(code):
    return LANGUAGES[code][0]


def script(code):
    return LANGUAGES[code][2]
