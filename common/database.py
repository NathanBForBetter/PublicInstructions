"""PostgreSQL helpers shared by the analyze_*.py scripts."""

import csv
from dataclasses import dataclass

import pandas as pd
import psycopg
from psycopg import sql

from common.config import settings

# Every table goes in its own schema, so these scripts never touch tables you
# already have. To remove everything again:  DROP SCHEMA ai_categories CASCADE;
SCHEMA = "ai_categories"

REVIEW_COLUMNS = """
    review_id           integer NOT NULL,
    restaurant_name     text    NOT NULL,
    restaurant_rating   numeric,
    restaurant_feedback text    NOT NULL,
"""


@dataclass(frozen=True)
class Table:
    csv_name: str
    created_by: str
    columns: str


TABLES = {
    "feedback_emotions": Table(
        csv_name="feedback_emotions.csv",
        created_by="categorize_feedback_emotion.py",
        columns=REVIEW_COLUMNS + """
            emotion      text    NOT NULL,
            emotion_rank integer NOT NULL,
            PRIMARY KEY (review_id, emotion_rank)
        """,
    ),
    "feedback_scale": Table(
        csv_name="feedback_scale.csv",
        created_by="categorize_feedback_scale.py",
        columns=REVIEW_COLUMNS + """
            feedback_scale        text NOT NULL
                CHECK (feedback_scale IN ('Great', 'Good', 'Neutral', 'Bad', 'Terrible')),
            feedback_scale_reason text,
            PRIMARY KEY (review_id)
        """,
    ),
    "restaurant_types": Table(
        csv_name="restaurant_types.csv",
        created_by="categorize_restaurant_type.py",
        columns="""
            restaurant_name text PRIMARY KEY,
            restaurant_type text NOT NULL
        """,
    ),
    "feedback_aspects": Table(
        csv_name="feedback_aspects.csv",
        created_by="categorize_feedback_aspects.py",
        columns=REVIEW_COLUMNS + """
            aspect            text NOT NULL,
            sentiment         text NOT NULL CHECK (sentiment IN ('positive', 'mixed', 'negative')),
            evidence_quote    text,
            quote_is_verbatim boolean,
            PRIMARY KEY (review_id, aspect)
        """,
    ),
    "feedback_themes": Table(
        csv_name="feedback_themes.csv",
        created_by="categorize_feedback_themes.py",
        columns=REVIEW_COLUMNS + """
            theme_id          integer NOT NULL,
            theme             text    NOT NULL,
            theme_description text,
            theme_fit         numeric,
            PRIMARY KEY (review_id)
        """,
    ),
}


def connect() -> psycopg.Connection:
    """Open a connection with the PG* values from .env and the ai_categories schema selected.

    Use it as `with connect() as conn:` so the work is committed and the
    connection closed at the end of the block.
    """
    try:
        conn = psycopg.connect(
            host=settings.pg_host,
            port=settings.pg_port,
            dbname=settings.pg_database,
            user=settings.pg_user,
            password=settings.pg_password or None,
        )
    except psycopg.OperationalError as error:
        raise SystemExit(f"Could not connect to PostgreSQL: {error}\nCheck the PG* values in your .env file.")

    conn.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(SCHEMA)))
    conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(SCHEMA)))
    return conn


def load_table(conn: psycopg.Connection, table: str) -> None:
    """(Re)create `table` and bulk-load its CSV from the output folder with COPY."""
    spec = TABLES[table]
    csv_path = settings.output_dir / spec.csv_name
    if not csv_path.exists():
        raise SystemExit(f"{csv_path} not found. Run `python {spec.created_by}` first.")

    with open(csv_path, newline="", encoding="utf-8") as file:
        header = next(csv.reader(file))

    name = sql.Identifier(SCHEMA, table)
    conn.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(name))
    conn.execute(sql.SQL("CREATE TABLE {} ({})").format(name, sql.SQL(spec.columns)))

    copy_statement = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER true)").format(
        name, sql.SQL(", ").join(sql.Identifier(column) for column in header)
    )
    with conn.cursor() as cursor:
        with cursor.copy(copy_statement) as copy, open(csv_path, "rb") as file:
            while chunk := file.read(65536):
                copy.write(chunk)
        print(f"Loaded {cursor.rowcount} rows from {spec.csv_name} into {SCHEMA}.{table}")


def show(conn: psycopg.Connection, title: str, query: str, params: dict | None = None) -> None:
    """Run a query and print its result as a table."""
    cursor = conn.execute(query, params)
    # NULL arrives from psycopg as None; print it as "-" so empty cells read as empty.
    rows = [["-" if value is None else value for value in row] for row in cursor.fetchall()]
    table = pd.DataFrame(rows, columns=[column.name for column in cursor.description])
    print(f"\n=== {title} ===")
    print(table.to_string(index=False) if rows else "(no rows)")
