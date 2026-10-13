"""Search inside the review text and see which themes the matches belong to.

SQL techniques: full-text search (tsvector, tsquery, ts_rank, ts_headline),
generated columns, GIN indexes, query parameters.
Loads feedback_themes.csv (written by categorize_feedback_themes.py).

    python analyze_theme_search.py                        # searches for "slow OR waited"
    python analyze_theme_search.py --search "cold fries"
    python analyze_theme_search.py --search '"hung up" OR rude -burger'

--search understands plain words, "quoted phrases", OR, and -word to exclude,
like a web search box.
"""

import argparse

from common.database import connect, load_table, show

# A tsvector is the review text reduced to searchable word stems ("waited" and
# "waiting" both become "wait"). Storing it as a generated column keeps it in
# sync with the text, and the GIN index lets PostgreSQL find matches without
# reading every row.
ADD_SEARCH_COLUMN = """
ALTER TABLE feedback_themes
    ADD COLUMN search_vector tsvector
    GENERATED ALWAYS AS (to_tsvector('english', restaurant_feedback)) STORED;
"""

ADD_SEARCH_INDEX = """
CREATE INDEX feedback_themes_search_idx ON feedback_themes USING GIN (search_vector);
"""

# array_agg with an ORDER BY, then [1], picks the review closest to the centre of each theme.
THEME_OVERVIEW = """
SELECT
    theme_id,
    theme,
    COUNT(*)                         AS reviews,
    COUNT(DISTINCT restaurant_name)  AS restaurants,
    ROUND(AVG(restaurant_rating), 2) AS avg_rating,
    (array_agg(left(restaurant_feedback, 60) ORDER BY theme_fit DESC))[1] AS most_typical_review
FROM feedback_themes
GROUP BY theme_id, theme
ORDER BY reviews DESC, theme_id;
"""

# %(search)s is a query parameter: psycopg sends the value separately from the
# SQL, so whatever the user types can never be run as SQL (no SQL injection).
# @@ means "matches", ts_rank scores how well, ts_headline marks the matching words.
SEARCH_RESULTS = """
SELECT
    review_id,
    restaurant_name,
    theme,
    ROUND(ts_rank(search_vector, query)::numeric, 3) AS relevance,
    ts_headline('english', restaurant_feedback, query,
                'StartSel=[, StopSel=], MaxWords=14, MinWords=6') AS matching_text
FROM feedback_themes, websearch_to_tsquery('english', %(search)s) AS query
WHERE search_vector @@ query
ORDER BY relevance DESC, review_id
LIMIT 10;
"""

MATCHES_BY_THEME = """
SELECT
    theme,
    COUNT(*) FILTER (WHERE search_vector @@ query) AS matching_reviews,
    COUNT(*)                                       AS reviews_in_theme,
    ROUND(100.0 * COUNT(*) FILTER (WHERE search_vector @@ query) / COUNT(*)) AS pct_matching
FROM feedback_themes, websearch_to_tsquery('english', %(search)s) AS query
GROUP BY theme
ORDER BY pct_matching DESC, theme;
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--search", default="slow OR waited", help="what to look for in the review text")
    args = parser.parse_args()
    search = {"search": args.search}

    with connect() as conn:
        load_table(conn, "feedback_themes")
        conn.execute(ADD_SEARCH_COLUMN)
        conn.execute(ADD_SEARCH_INDEX)
        show(conn, "Themes found by categorize_feedback_themes.py", THEME_OVERVIEW)
        show(conn, f"Reviews matching: {args.search}", SEARCH_RESULTS, search)
        show(conn, f"Share of each theme matching: {args.search}", MATCHES_BY_THEME, search)


if __name__ == "__main__":
    main()
