"""Aspect-based sentiment: what exactly did each customer like or dislike?

A review like "amazing ramen but we waited an hour" is neither simply good nor
simply bad. This script splits each review into the aspects it talks about
(food, service, price, ...) and gives every aspect its own sentiment. The model
must also quote the words it based each sentiment on, and each quote is checked
against the review text, which flags evidence the model made up.

Appends one row per review and aspect to feedback_aspects.csv in the output folder.

    python categorize_feedback_aspects.py            # run, or resume an interrupted run
    python categorize_feedback_aspects.py --limit 5  # only the first 5 reviews
    python categorize_feedback_aspects.py --fresh    # start over

A review that mentions none of the aspects saves no rows and is asked about
again on the next run.
"""

from typing import Literal

from pydantic import BaseModel

from common.ai_client import ask
from common.reviews import review_prompt, run_per_review

INSTRUCTIONS = """\
You break restaurant feedback down into the aspects the customer talks about.
List each aspect at most once, and only if the feedback actually mentions it.
Use "mixed" when the customer is lukewarm about an aspect or says both good and
bad things about it.
For evidence_quote, copy the few words of the feedback that best support the
sentiment, exactly as the customer wrote them."""


class AspectSentiment(BaseModel):
    aspect: Literal["food", "service", "price", "ambiance", "wait_time", "cleanliness"]
    sentiment: Literal["positive", "mixed", "negative"]
    evidence_quote: str


class FeedbackAspects(BaseModel):
    aspects: list[AspectSentiment]


def is_verbatim(quote: str, feedback: str) -> bool:
    """True if the quote really appears in the feedback, ignoring case, spacing and outer punctuation."""

    def normalize(text: str) -> str:
        return " ".join(text.lower().split())

    return normalize(quote.strip(" .,!?\"'…")) in normalize(feedback)


def categorize(review: dict) -> list[dict]:
    answer = ask(INSTRUCTIONS, review_prompt(review), FeedbackAspects)
    rows: dict[str, dict] = {}
    for item in answer.aspects:
        # setdefault keeps the first entry if the model lists an aspect twice.
        rows.setdefault(
            item.aspect,
            {
                "aspect": item.aspect,
                "sentiment": item.sentiment,
                "evidence_quote": item.evidence_quote.strip(),
                "quote_is_verbatim": is_verbatim(item.evidence_quote, review["restaurant_feedback"]),
            },
        )
    return list(rows.values())


if __name__ == "__main__":
    run_per_review(
        __doc__,
        "feedback_aspects.csv",
        ["aspect", "sentiment", "evidence_quote", "quote_is_verbatim"],
        categorize,
    )
