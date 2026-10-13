"""Benchmark each restaurant against others of the same type, by joining two tables.

SQL techniques: INNER JOIN, FULL OUTER JOIN, common table expressions (WITH).
Loads restaurant_types.csv (written by categorize_restaurant_type.py) and
feedback_scale.csv (written by categorize_feedback_scale.py).

    python analyze_restaurant_benchmarks.py
"""

from common.database import connect, load_table, show

# Each CTE is a named, temporary result the final SELECT can join like a table.
RESTAURANT_VS_TYPE = """
WITH restaurant_stats AS (
    SELECT restaurant_name, COUNT(*) AS reviews, AVG(restaurant_rating) AS avg_rating
    FROM feedback_scale
    GROUP BY restaurant_name
),
type_stats AS (
    SELECT restaurant_type, AVG(restaurant_rating) AS type_avg_rating
    FROM feedback_scale
    JOIN restaurant_types USING (restaurant_name)
    GROUP BY restaurant_type
)
SELECT
    restaurant_type,
    restaurant_name,
    reviews,
    ROUND(avg_rating, 2)                   AS avg_rating,
    ROUND(type_avg_rating, 2)              AS type_avg_rating,
    ROUND(avg_rating - type_avg_rating, 2) AS vs_type
FROM restaurant_stats
JOIN restaurant_types USING (restaurant_name)
JOIN type_stats USING (restaurant_type)
ORDER BY restaurant_type, vs_type DESC;
"""

TYPE_LEADERBOARD = """
SELECT
    restaurant_type,
    COUNT(DISTINCT restaurant_name)  AS restaurants,
    COUNT(*)                         AS reviews,
    ROUND(AVG(restaurant_rating), 2) AS avg_rating,
    ROUND(100.0 * COUNT(*) FILTER (WHERE feedback_scale IN ('Great', 'Good')) / COUNT(*)) AS pct_positive
FROM restaurant_types
JOIN feedback_scale USING (restaurant_name)
GROUP BY restaurant_type
ORDER BY avg_rating DESC, restaurant_type;
"""

# An inner join silently drops rows without a match. A FULL OUTER JOIN keeps
# them, with NULLs on the side that is missing, which makes gaps easy to find.
UNMATCHED_RESTAURANTS = """
SELECT
    restaurant_name,
    CASE
        WHEN types.restaurant_name IS NULL THEN 'has reviews but no type'
        ELSE 'has a type but no reviews'
    END AS problem
FROM (SELECT DISTINCT restaurant_name FROM feedback_scale) AS reviewed
FULL OUTER JOIN restaurant_types AS types USING (restaurant_name)
WHERE reviewed.restaurant_name IS NULL OR types.restaurant_name IS NULL
ORDER BY restaurant_name;
"""


def main() -> None:
    with connect() as conn:
        load_table(conn, "restaurant_types")
        load_table(conn, "feedback_scale")
        show(conn, "Each restaurant vs. the average of its type", RESTAURANT_VS_TYPE)
        show(conn, "Restaurant types, best rated first", TYPE_LEADERBOARD)
        show(conn, "Restaurants missing from one of the two tables", UNMATCHED_RESTAURANTS)


if __name__ == "__main__":
    main()
