"""Give every restaurant a short type label, such as "sushi" or "burger fast food".

Each restaurant is categorized once, however many reviews it has. The types
handed out so far are passed back to the model, so similar restaurants share
one label instead of near-duplicates like "burgers" and "burger joint".

Appends one row per restaurant to restaurant_types.csv in the output folder.

    python categorize_restaurant_type.py            # run, or resume an interrupted run
    python categorize_restaurant_type.py --limit 5  # only restaurants in the first 5 reviews
    python categorize_restaurant_type.py --fresh    # start over
"""

from pydantic import BaseModel

from common.ai_client import ask, get_client
from common.config import settings
from common.reviews import OutputCsv, cli_parser, load_reviews

SAMPLE_REVIEWS = 3

INSTRUCTIONS = """\
You sort restaurants into types, based on their name and a few customer reviews.
A type is one to three lowercase words, such as "sushi" or "burger fast food".
If one of the existing types fits, reuse it exactly as written. Only create a
new type when none of them fit."""


class RestaurantType(BaseModel):
    restaurant_type: str


def categorize(restaurant_name: str, sample_feedback: list[str], existing_types: list[str]) -> str:
    content = "\n".join(
        [
            f"Restaurant: {restaurant_name}",
            f"Existing types: {', '.join(existing_types) or 'none yet'}",
            "Reviews:",
            *[f"- {feedback}" for feedback in sample_feedback],
        ]
    )
    return ask(INSTRUCTIONS, content, RestaurantType).restaurant_type.strip().lower()


def main() -> None:
    args = cli_parser(__doc__).parse_args()
    get_client()  # stop right away if the API key is missing
    reviews = load_reviews(args.limit)
    output = OutputCsv("restaurant_types.csv", ["restaurant_name", "restaurant_type"], fresh=args.fresh)

    saved = output.read()
    existing_types = sorted(set(saved["restaurant_type"]))
    finished = set(saved["restaurant_name"])
    todo = [name for name in reviews["restaurant_name"].unique() if name not in finished]
    print(f"{len(todo)} restaurants left to categorize with {settings.openai_model} -> {output.path}")

    for position, restaurant_name in enumerate(todo, start=1):
        of_this_restaurant = reviews[reviews["restaurant_name"] == restaurant_name]
        sample_feedback = of_this_restaurant["restaurant_feedback"].head(SAMPLE_REVIEWS).tolist()

        restaurant_type = categorize(restaurant_name, sample_feedback, existing_types)
        output.append([{"restaurant_name": restaurant_name, "restaurant_type": restaurant_type}])
        if restaurant_type not in existing_types:
            existing_types.append(restaurant_type)
        print(f"[{position}/{len(todo)}] {restaurant_name}: {restaurant_type}")

    print(f"Done. Results are in {output.path}")


if __name__ == "__main__":
    main()
