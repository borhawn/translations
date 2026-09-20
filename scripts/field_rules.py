"""Per-column handling rules for the WPML page export.

Column order and names are taken verbatim from the export header
(107 columns, four of which are duplicated names: Title, URL and the three
_wpml_import_* fields). Rules are keyed by column INDEX, never by name,
because the duplicate names make name lookup ambiguous.

Actions
-------
COPY        take the English source value byte-for-byte
TRANSLATE   plain text / HTML+shortcode text -> translate text only
TR_LIST     pipe-delimited taxonomy term list -> translate each term
TR_SERIAL   PHP-serialised blob -> unserialise, translate whitelisted string
            values, re-serialise with recomputed BYTE lengths
DERIVE      computed per target language (see note)
BLANK       must be emptied so WordPress/WPML/RankMath regenerate it
CONST       fixed literal value (see note)
"""

RULES = [
    (0,   "ID",                                      "BLANK",     "empty => WP All Import creates a new post"),
    (1,   "Title",                                   "TRANSLATE", ""),
    (2,   "Content",                                 "TRANSLATE", "shortcodes + HTML must stay byte-identical"),
    (3,   "Excerpt",                                 "TRANSLATE", "empty on every EN page today"),
    (4,   "Date",                                    "COPY",      ""),
    (5,   "Post Type",                               "COPY",      "page"),
    (6,   "Permalink",                               "BLANK",     "read-only export field; WP rebuilds it"),
    (7,   "WPML Translation ID",                     "COPY",      "= EN post ID, same for whole group"),
    (8,   "WPML Language Code",                      "DERIVE",    "target language code"),
    (9,   "_wpml_import_language_code",              "DERIVE",    "target language code"),
    (10,  "_wpml_import_source_language_code",       "CONST",     "en"),
    (11,  "_wpml_import_translation_group",          "COPY",      "= EN post ID (533 for the homepage)"),
    (12,  "URL",                                     "COPY",      "media URL list"),
    (13,  "Title",                                   "TRANSLATE", "media title list (pipe-delimited)"),
    (14,  "Caption",                                 "TRANSLATE", "media caption list (pipe-delimited)"),
    (15,  "Description",                             "TRANSLATE", "media description list (pipe-delimited)"),
    (16,  "Alt Text",                                "TRANSLATE", "media alt list (pipe-delimited)"),
    (17,  "Featured",                                "COPY",      ""),
    (18,  "URL",                                     "COPY",      "featured image URL"),
    (19,  "Categories",                              "TR_LIST",   ""),
    (20,  "Tags",                                    "TR_LIST",   ""),
    (21,  "Translation Priorities",                  "CONST",     "Optional"),
    (22,  "Relation Tags",                           "TR_LIST",   ""),
    (23,  "_wpml_word_count",                        "DERIVE",    "word count of the translated content"),
    (24,  "copied_media_ids",                        "COPY",      "serialised media id list, ids are language-neutral"),
    (25,  "referenced_media_ids",                    "COPY",      "same"),
    (26,  "_last_editor_used_jetpack",               "COPY",      ""),
    (27,  "_wp_page_template",                       "COPY",      ""),
    (28,  "g1_page_builder_state",                   "COPY",      ""),
    (29,  "slide_template",                          "COPY",      ""),
    (30,  "_g1_gmaps_metabox",                       "COPY",      "serialised, no translatable strings"),
    (31,  "_g1_subtitle",                            "TRANSLATE", "visible page subtitle, 28 EN pages"),
    (32,  "_g1",                                     "TR_SERIAL", "only single_element_slider, and only if a per-language slider exists"),
    (33,  "_single_add_custom_css",                  "COPY",      "CSS"),
    (34,  "_g_feedback_shortcode_513437d2...",       "TRANSLATE", "contact-field label= attributes only"),
    (35,  "_g_feedback_shortcode_atts_513437d2...",  "TR_SERIAL", "subject, submit_button_text, customThankyou*"),
    (36,  "_g_feedback_shortcode_d461bf69...",       "TRANSLATE", "contact-field label= attributes only"),
    (37,  "_g_feedback_shortcode_atts_d461bf69...",  "TR_SERIAL", "subject, submit_button_text, customThankyou*"),
    (38,  "_g_feedback_shortcode_7ab9b3dd...",       "TRANSLATE", "contact-field label= attributes only"),
    (39,  "_g_feedback_shortcode_atts_7ab9b3dd...",  "TR_SERIAL", "subject, submit_button_text, customThankyou*"),
    (40,  "rank_math_analytic_object_id",            "BLANK",     "RankMath assigns a new one per post"),
    (41,  "rank_math_internal_links_processed",      "COPY",      ""),
    (42,  "rank_math_seo_score",                     "COPY",      ""),
    (43,  "_gglstmp_meta_canonical_tag",             "BLANK",     "EN value is a broken URL; do not propagate"),
    (44,  "om_disable_all_campaigns",                "COPY",      ""),
    (45,  "rank_math_primary_category",              "COPY",      "empty on every EN page"),
    (46,  "rank_math_title",                         "TRANSLATE", "SEO title, <=60 visible chars"),
    (47,  "rank_math_description",                   "TRANSLATE", "SEO meta description, <=155 visible chars"),
    (48,  "rank_math_facebook_image",                "COPY",      ""),
    (49,  "rank_math_facebook_image_id",             "COPY",      ""),
    (50,  "rank_math_facebook_enable_image_overlay", "COPY",      ""),
    (51,  "rank_math_facebook_title",                "TRANSLATE", "OG title"),
    (52,  "rank_math_facebook_description",          "TRANSLATE", "OG description"),
    (53,  "os_meta",                                 "COPY",      'serialised, only os_segment="All"'),
    (54,  "_jetpack_related_posts_cache",            "BLANK",     "stale cache, regenerates itself"),
    (55,  "rank_math_og_content_image",              "COPY",      "serialised image URL + md5 check"),
    (56,  "rank_math_schema_Service",                "TR_SERIAL", "name, description, serviceType"),
    (57,  "rank_math_shortcode_schema_s-6796ae58081ee", "COPY",   ""),
    (58,  "rank_math_shortcode_schema_s-67cb62b7ab74c", "COPY",   ""),
    (59,  "_alp_processed",                          "BLANK",     "hreflang plugin timestamp"),
    (60,  "country",                                 "COPY",      "ACF value"),
    (61,  "_country",                                "COPY",      "ACF field key - never translate"),
    (62,  "phone",                                   "COPY",      "ACF value"),
    (63,  "_phone",                                  "COPY",      "ACF field key"),
    (64,  "rep_office_address",                      "TRANSLATE", "ACF value (address text)"),
    (65,  "_rep_office_address",                     "COPY",      "ACF field key"),
    (66,  "city1",                                   "TRANSLATE", "ACF value (city name)"),
    (67,  "_city1",                                  "COPY",      "ACF field key"),
    (68,  "city2",                                   "TRANSLATE", "ACF value (city name)"),
    (69,  "_city2",                                  "COPY",      "ACF field key"),
    (70,  "list_cities",                             "TRANSLATE", "ACF value (city list)"),
    (71,  "_list_cities",                            "COPY",      "ACF field key"),
    (72,  "_glossary_disable_for_page",              "COPY",      ""),
    (73,  "_glossary_disable_tooltip_for_page",      "COPY",      ""),
    (74,  "_glossary_disable_links_for_page",        "COPY",      ""),
    (75,  "_cmtt_highlightFirstOnly",                "COPY",      ""),
    (76,  "_glossary_disable_dom_parser_...",        "COPY",      ""),
    (77,  "_cmtt_disable_acf_for_page",              "COPY",      ""),
    (78,  "_cmtt_new_page_exception",                "COPY",      ""),
    (79,  "rank_math_focus_keyword",                 "TRANSLATE", "localised keyword, NOT a literal translation"),
    (80,  "rank_math_pillar_content",                "COPY",      ""),
    (81,  "rank_math_shortcode_schema_s-687d46cb520d5", "COPY",   ""),
    (82,  "_wpml_media_duplicate",                   "COPY",      ""),
    (83,  "_wpml_media_featured",                    "COPY",      ""),
    (84,  "_icl_lang_duplicate_of",                  "BLANK",     "MUST stay empty or WPML treats the page as a duplicate, not a translation"),
    (85,  "_last_translation_edit_mode",             "CONST",     "native-editor"),
    (86,  "import_key",                              "DERIVE",    "<en_id>-<lang>  (matches the pattern already used by the 5 FR pages)"),
    (87,  "_wpml_media_has_media",                   "COPY",      ""),
    (88,  "_wpml_location_migration_done",           "COPY",      ""),
    (89,  "_wpml_import_language_code",              "DERIVE",    "duplicate of col 9, must match"),
    (90,  "_wpml_import_source_language_code",       "CONST",     "en (duplicate of col 10)"),
    (91,  "_wpml_import_translation_group",          "COPY",      "duplicate of col 11, must match"),
    (92,  "Status",                                  "COPY",      "keeps the 6 drafts as drafts"),
    (93,  "Author ID",                               "COPY",      ""),
    (94,  "Author Username",                         "COPY",      ""),
    (95,  "Author Email",                            "COPY",      ""),
    (96,  "Author First Name",                       "COPY",      ""),
    (97,  "Author Last Name",                        "COPY",      ""),
    (98,  "Slug",                                    "DERIVE",    "ASCII-transliterated slug from the translated title"),
    (99,  "Format",                                  "COPY",      ""),
    (100, "Template",                                "COPY",      ""),
    (101, "Parent",                                  "DERIVE",    "translated parent post id - resolved in import pass 2"),
    (102, "Parent Slug",                             "DERIVE",    "translated parent slug - resolved in import pass 2"),
    (103, "Order",                                   "COPY",      ""),
    (104, "Comment Status",                          "COPY",      ""),
    (105, "Ping Status",                             "COPY",      ""),
    (106, "Post Modified Date",                      "DERIVE",    "generation timestamp"),
]

BY_ACTION = {}
for _i, _n, _a, _note in RULES:
    BY_ACTION.setdefault(_a, []).append(_i)

if __name__ == "__main__":
    for a in ("TRANSLATE", "TR_LIST", "TR_SERIAL", "DERIVE", "CONST", "BLANK", "COPY"):
        print(f"{a:10} {len(BY_ACTION.get(a, [])):3}  {BY_ACTION.get(a)}")
