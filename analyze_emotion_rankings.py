"""Rank emotions within restaurants and customer groups, using window functions.

SQL techniques: ROW_NUMBER, DENSE_RANK, SUM(...) OVER, PARTITION BY, running totals.
Loads feedback_emotions.csv (written by categorize_feedback_emotion.py).

    python analyze_emotion_rankings.py
"""

from common.database import connect, load_table, show

# A window function looks at other rows without collapsing them the way
# GROUP BY does. PARTITION BY restarts the numbering for every restaurant.
TOP_EMOTIONS_PER_RESTAURANT = """
WITH emotion_counts AS (
    SELECT restaurant_name, emotion, COUNT(*) AS mentions
    FROM feedback_emotions
    GROUP BY restaurant_name, emotion
),
ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY restaurant_name ORDER BY mentions DESC, emotion) AS position,
        ROUND(100.0 * mentions / SUM(mentions) OVER (PARTITION BY restaurant_name))      AS pct_of_restaurant
    FROM emotion_counts
)
SELECT restaurant_name, position, emotion, mentions, pct_of_restaurant
FROM ranked
WHERE position <= 3
ORDER BY restaurant_name, position;
"""

# Window functions run after GROUP BY, so they can add up the grouped counts:
# an empty OVER () is the grand total, OVER (ORDER BY ...) is a running total.
MOST_COMMON_EMOTIONS = """
SELECT
    emotion,
    COUNT(*)                                             AS mentions,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)   AS pct_of_all,
    ROUND(100.0 * SUM(COUNT(*)) OVER (ORDER BY COUNT(*) DESC, emotion)
                / SUM(COUNT(*)) OVER (), 1)              AS running_pct
FROM feedback_emotions
GROUP BY emotion
ORDER BY mentions DESC, emotion
LIMIT 10;
"""

# ROW_NUMBER above always returns exactly three rows per restaurant.
# DENSE_RANK gives tied emotions the same position, so ties all show up here.
EMOTIONS_BY_CUSTOMER_GROUP = """
WITH grouped AS (
    SELECT
        CASE WHEN restaurant_rating >= 4 THEN 'happy (4-5 stars)' ELSE 'unhappy (1-2 stars)' END AS customer_group,
        emotion,
        COUNT(*) AS mentions
    FROM feedback_emotions
    WHERE restaurant_rating >= 4 OR restaurant_rating <= 2
    GROUP BY customer_group, emotion
),
ranked AS (
    SELECT *, DENSE_RANK() OVER (PARTITION BY customer_group ORDER BY mentions DESC) AS position
    FROM grouped
)
SELECT customer_group, position, emotion, mentions
FROM ranked
WHERE position <= 3
ORDER BY customer_group, position, emotion;
"""


def main() -> None:
    with connect() as conn:
        load_table(conn, "feedback_emotions")
        show(conn, "Top 3 emotions per restaurant", TOP_EMOTIONS_PER_RESTAURANT)
        show(conn, "Most common emotions overall, with running share", MOST_COMMON_EMOTIONS)
        show(conn, "Leading emotions of happy vs. unhappy customers", EMOTIONS_BY_CUSTOMER_GROUP)


if __name__ == "__main__":
    main()
