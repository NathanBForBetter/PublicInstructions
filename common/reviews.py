"""Reading the input reviews and appending AI categories to CSVs in the output folder."""

import argparse
import csv
from typing import Callable

import pandas as pd

from common.ai_client import get_client
from common.config import settings

# Every per-review output CSV starts with these columns, so each file makes sense on its own.
REVIEW_COLUMNS = ["review_id", "restaurant_name", "restaurant_rating", "restaurant_feedback"]


def cli_parser(description: str, resumable: bool = True) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, help="only read the first N reviews (a cheap way to test)")
    if resumable:
        parser.add_argument("--fresh", action="store_true", help="start over instead of resuming the existing output CSV")
    return parser


def load_reviews(limit: int | None = None) -> pd.DataFrame:
    """Read the input CSV into REVIEW_COLUMNS, one row per review, every value kept as text."""
    path = settings.input_csv_path
    if not path.exists():
        raise SystemExit(f"Input CSV not found: {path}\nSet INPUT_CSV_PATH in your .env file.")

    reviews = pd.read_csv(path, dtype=str, keep_default_na=False)
    reviews = reviews.rename(columns={"restaurant_rating_out_of_5": "restaurant_rating"})
    if "review_id" not in reviews.columns:
        # The row number in the input file, so a review keeps the same id in every script.
        reviews.insert(0, "review_id", [str(number) for number in range(1, len(reviews) + 1)])

    missing = [column for column in REVIEW_COLUMNS if column not in reviews.columns]
    if missing:
        raise SystemExit(f"{path} is missing column(s): {', '.join(missing)}")

    reviews = reviews[REVIEW_COLUMNS]
    reviews = reviews[reviews["restaurant_feedback"].str.strip() != ""]
    if limit:
        reviews = reviews.head(limit)
    return reviews.reset_index(drop=True)


def review_prompt(review: dict) -> str:
    """The text shown to the model for one review."""
    rating = f"{review['restaurant_rating']} out of 5" if review["restaurant_rating"] else "not given"
    return (
        f"Restaurant: {review['restaurant_name']}\n"
        f"Rating: {rating}\n"
        f"Feedback: {review['restaurant_feedback']}"
    )


class OutputCsv:
    """A CSV in the output folder that rows are appended to as they are produced.

    Appending after every AI call means a crash or Ctrl+C never loses finished
    work, and the next run can pick up where the last one stopped.
    """

    def __init__(self, filename: str, columns: list[str], fresh: bool = False):
        self.path = settings.output_dir / filename
        self.columns = columns
        if fresh or not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "w", newline="", encoding="utf-8") as file:
                csv.writer(file).writerow(columns)
        elif list(self.read().columns) != columns:
            raise SystemExit(f"{self.path} has different columns than this script writes. Rerun with --fresh.")

    def read(self) -> pd.DataFrame:
        return pd.read_csv(self.path, dtype=str, keep_default_na=False)

    def append(self, rows: list[dict]) -> None:
        with open(self.path, "a", newline="", encoding="utf-8") as file:
            csv.DictWriter(file, fieldnames=self.columns).writerows(rows)


def run_per_review(
    description: str,
    filename: str,
    category_columns: list[str],
    categorize: Callable[[dict], list[dict]],
) -> None:
    """Command-line entry point for the scripts that make one AI call per review.

    `categorize` receives one review and returns the rows to save for it, as
    dicts keyed by `category_columns`. Reviews already in the output CSV are
    skipped, so an interrupted run resumes where it stopped.
    """
    args = cli_parser(description).parse_args()
    get_client()  # stop right away if the API key is missing
    reviews = load_reviews(args.limit)
    output = OutputCsv(filename, REVIEW_COLUMNS + category_columns, fresh=args.fresh)

    finished = set(output.read()["review_id"])
    todo = reviews[~reviews["review_id"].isin(finished)].to_dict("records")
    print(f"{len(todo)} of {len(reviews)} reviews left to categorize with {settings.openai_model} -> {output.path}")

    for position, review in enumerate(todo, start=1):
        rows = categorize(review)
        output.append([{**review, **row} for row in rows])
        labels = ", ".join(str(row[category_columns[0]]) for row in rows) or "nothing to save"
        print(f"[{position}/{len(todo)}] review {review['review_id']}: {labels}")

    print(f"Done. Results are in {output.path}")
