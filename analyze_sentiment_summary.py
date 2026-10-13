"""Sentiment summary per restaurant, built with grouped aggregates.

SQL techniques: GROUP BY, COUNT(*) FILTER (WHERE ...), HAVING, CASE.
Loads feedback_scale.csv (written by categorize_feedback_scale.py).

    python analyze_sentiment_summary.py
"""

from common.database import connect, load_table, show

# FILTER counts only the rows that match, which turns one GROUP BY into a
# column per scale value.
SCALE_MIX = """
SELECT
    restaurant_name,
    COUNT(*)                                            AS reviews,
    ROUND(AVG(restaurant_rating), 2)                    AS avg_rating,
    COUNT(*) FILTER (WHERE feedback_scale = 'Great')    AS great,
    COUNT(*) FILTER (WHERE feedback_scale = 'Good')     AS good,
    COUNT(*) FILTER (WHERE feedback_scale = 'Neutral')  AS neutral,
    COUNT(*) FILTER (WHERE feedback_scale = 'Bad')      AS bad,
    COUNT(*) FILTER (WHERE feedback_scale = 'Terrible') AS terrible,
    ROUND(100.0 * COUNT(*) FILTER (WHERE feedback_scale IN ('Great', 'Good')) / COUNT(*)) AS pct_positive
FROM feedback_scale
GROUP BY restaurant_name
ORDER BY pct_positive DESC, avg_rating DESC;
"""

# WHERE filters rows before grouping; HAVING filters the groups afterwards.
REPEATED_COMPLAINTS = """
SELECT
    restaurant_name,
    COUNT(*)                         AS negative_reviews,
    ROUND(AVG(restaurant_rating), 2) AS avg_rating_of_those
FROM feedback_scale
WHERE feedback_scale IN ('Bad', 'Terrible')
GROUP BY restaurant_name
HAVING COUNT(*) >= 2
ORDER BY negative_reviews DESC, restaurant_name;
"""

# CASE maps the AI's scale onto 1-5 so it can be compared with the stars the
# customer gave. A gap of two or more usually means a mis-clicked rating.
STARS_VS_AI = """
SELECT
    review_id,
    restaurant_name,
    restaurant_rating     AS stars,
    feedback_scale        AS ai_scale,
    feedback_scale_reason AS ai_reason
FROM feedback_scale
WHERE ABS(
    restaurant_rating - CASE feedback_scale
        WHEN 'Great'    THEN 5
        WHEN 'Good'     THEN 4
        WHEN 'Neutral'  THEN 3
        WHEN 'Bad'      THEN 2
        WHEN 'Terrible' THEN 1
    END
) >= 2
ORDER BY review_id;
"""


def main() -> None:
    with connect() as conn:
        load_table(conn, "feedback_scale")
        show(conn, "Sentiment mix by restaurant", SCALE_MIX)
        show(conn, "Restaurants with two or more negative reviews", REPEATED_COMPLAINTS)
        show(conn, "Reviews where the star rating and the AI disagree", STARS_VS_AI)


if __name__ == "__main__":
    main()
