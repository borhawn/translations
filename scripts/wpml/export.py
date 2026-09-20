"""Load the WPML page export without losing a byte of the original rows."""

import csv
import sys

csv.field_size_limit(10 ** 9)

EXPECTED_COLUMNS = 107

# Column indices. Names are duplicated in the header, so index is the only
# safe way to address a column.
ID, TITLE, CONTENT, EXCERPT, DATE, POST_TYPE, PERMALINK = 0, 1, 2, 3, 4, 5, 6
WPML_TRANSLATION_ID, LANG, IMPORT_LANG, IMPORT_SRC_LANG, GROUP = 7, 8, 9, 10, 11
MEDIA_URL, MEDIA_TITLE, MEDIA_CAPTION, MEDIA_DESC, MEDIA_ALT = 12, 13, 14, 15, 16
CATEGORIES, TAGS, PRIORITIES, RELATION_TAGS, WORD_COUNT = 19, 20, 21, 22, 23
SUBTITLE, G1 = 31, 32
FEEDBACK_FORMS = (34, 36, 38)
FEEDBACK_ATTS = (35, 37, 39)
ANALYTIC_ID, CANONICAL = 40, 43
SEO_TITLE, SEO_DESC, OG_TITLE, OG_DESC = 46, 47, 51, 52
JETPACK_CACHE, SCHEMA_SERVICE, ALP_PROCESSED = 54, 56, 59
ACF_ADDRESS, ACF_CITY1, ACF_CITY2, ACF_CITIES = 64, 66, 68, 70
FOCUS_KEYWORD = 79
LANG_DUPLICATE_OF, LAST_EDIT_MODE, IMPORT_KEY = 84, 85, 86
IMPORT_LANG_2, IMPORT_SRC_LANG_2, GROUP_2 = 89, 90, 91
STATUS, SLUG, PARENT, PARENT_SLUG, MODIFIED = 92, 98, 101, 102, 106


class Export:
    def __init__(self, header, rows, raw_lines):
        self.header = header
        self.rows = rows
        self.raw_lines = raw_lines          # original text, reused verbatim

    @property
    def english(self):
        return [r for r in self.rows if r[LANG] == "en"]

    @property
    def target_languages(self):
        return sorted({r[LANG] for r in self.rows} - {"en"})

    def existing_pairs(self):
        """{(group, lang)} that already have a row, so we never duplicate one."""
        return {(r[GROUP], r[LANG]) for r in self.rows if r[LANG] != "en"}


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        rows = list(reader)
    if len(header) != EXPECTED_COLUMNS:
        sys.exit(f"expected {EXPECTED_COLUMNS} columns, found {len(header)}")
    for n, row in enumerate(rows, 2):
        if len(row) != EXPECTED_COLUMNS:
            sys.exit(f"row {n} has {len(row)} columns")

    # Keep the original text so untouched rows can be written back byte-identically
    # instead of being re-quoted by Python's csv writer.
    with open(path, encoding="utf-8-sig", newline="") as fh:
        text = fh.read()
    head, _, body = text.partition("\n")
    raw_lines = _split_records(body)
    if len(raw_lines) != len(rows):
        raw_lines = None                     # fall back to re-serialising
    return Export(header, rows, {"header": head, "records": raw_lines})


def _split_records(body):
    """Split on record-terminating newlines only — quoted fields contain their own."""
    records, start, in_quotes = [], 0, False
    for i, char in enumerate(body):
        if char == '"':
            in_quotes = not in_quotes
        elif char == "\n" and not in_quotes:
            records.append(body[start:i])
            start = i + 1
    if body[start:].strip():
        records.append(body[start:])
    return records


def write(path, header_line, original_records, new_rows):
    """Original records verbatim, new rows appended with the same dialect."""
    import io
    buf = io.StringIO()
    writer = csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    writer.writerows(new_rows)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(header_line + "\n")
        for record in original_records:
            fh.write(record + "\n")
        fh.write(buf.getvalue())
