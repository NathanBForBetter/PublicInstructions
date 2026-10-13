"""Scorecard of what each restaurant does well and badly, as a pivot table.

SQL techniques: temporary views, pivoting with FILTER, GROUPING SETS, DISTINCT ON.
Loads feedback_aspects.csv (written by categorize_feedback_aspects.py).

Scores run from -1.00 (every mention negative) to +1.00 (every mention positive).

    python analyze_aspect_scorecard.py
"""

from common.database import connect, load_table, show

# A view is a saved query. This one adds a numeric score to every row so the
# queries below can average it. TEMP means it disappears when the script ends.
CREATE_SCORES_VIEW = """
CREATE TEMP VIEW aspect_scores AS
SELECT
    *,
    CASE sentiment WHEN 'positive' THEN 1 WHEN 'negative' THEN -1 ELSE 0 END AS score
FROM feedback_aspects;
"""

# Pivot: rows are restaurants, and each aspect becomes its own column.
# An empty cell means no review of that restaurant mentioned the aspect.
SCORECARD = """
SELECT
    restaurant_name,
    ROUND(AVG(score) FILTER (WHERE aspect = 'food'), 2)        AS food,
    ROUND(AVG(score) FILTER (WHERE aspect = 'service'), 2)     AS service,
    ROUND(AVG(score) FILTER (WHERE aspect = 'price'), 2)       AS price,
    ROUND(AVG(score) FILTER (WHERE aspect = 'ambiance'), 2)    AS ambiance,
    ROUND(AVG(score) FILTER (WHERE aspect = 'wait_time'), 2)   AS wait_time,
    ROUND(AVG(score) FILTER (WHERE aspect = 'cleanliness'), 2) AS cleanliness
FROM aspect_scores
GROUP BY restaurant_name
ORDER BY restaurant_name;
"""

# GROUPING SETS runs several GROUP BYs in one query: per aspect, per restaurant
# and a grand total. GROUPING(column) is 1 on rows where that column was rolled up.
SUMMARY_LEVELS = """
SELECT
    CASE
        WHEN GROUPING(aspect) = 0          THEN 'aspect'
        WHEN GROUPING(restaurant_name) = 0 THEN 'restaurant'
        ELSE 'overall'
    END                                             AS level,
    COALESCE(aspect, restaurant_name, 'all reviews') AS item,
    COUNT(*)                                        AS mentions,
    ROUND(AVG(score), 2)                            AS avg_score
FROM aspect_scores
GROUP BY GROUPING SETS ((aspect), (restaurant_name), ())
ORDER BY GROUPING(aspect), GROUPING(restaurant_name), avg_score DESC, item;
"""

# DISTINCT ON keeps the first row of each restaurant, so the ORDER BY decides
# whether that row is its best aspect or its worst.
STRENGTHS_AND_WEAKNESSES = """
WITH by_aspect AS (
    SELECT restaurant_name, aspect, COUNT(*) AS mentions, ROUND(AVG(score), 2) AS score
    FROM aspect_scores
    GROUP BY restaurant_name, aspect
),
strongest AS (
    SELECT DISTINCT ON (restaurant_name) *
    FROM by_aspect
    ORDER BY restaurant_name, score DESC, mentions DESC, aspect
),
weakest AS (
    SELECT DISTINCT ON (restaurant_name) *
    FROM by_aspect
    ORDER BY restaurant_name, score, mentions DESC, aspect
)
SELECT
    restaurant_name,
    strongest.aspect AS strongest_aspect,
    strongest.score  AS strongest_score,
    weakest.aspect   AS weakest_aspect,
    weakest.score    AS weakest_score
FROM strongest
JOIN weakest USING (restaurant_name)
ORDER BY restaurant_name;
"""

# quote_is_verbatim is false when the model's evidence quote is not actually in the review.
UNVERIFIED_QUOTES = """
SELECT review_id, restaurant_name, aspect, sentiment, evidence_quote
FROM feedback_aspects
WHERE NOT quote_is_verbatim
ORDER BY review_id, aspect;
"""


def main() -> None:
    with connect() as conn:
        load_table(conn, "feedback_aspects")
        conn.execute(CREATE_SCORES_VIEW)
        show(conn, "Aspect scorecard by restaurant", SCORECARD)
        show(conn, "Scores per aspect, per restaurant and overall", SUMMARY_LEVELS)
        show(conn, "Strongest and weakest aspect of each restaurant", STRENGTHS_AND_WEAKNESSES)
        show(conn, "Evidence quotes that are not word for word in the review", UNVERIFIED_QUOTES)


if __name__ == "__main__":
    main()
