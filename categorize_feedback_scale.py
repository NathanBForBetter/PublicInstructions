"""Rate every review on a fixed scale: Great, Good, Neutral, Bad or Terrible.

The scale is part of the response schema, so the model cannot answer with
anything else. It also gives a one-sentence reason, which makes it easy to
spot-check its choices.

Appends one row per review to feedback_scale.csv in the output folder.

    python categorize_feedback_scale.py            # run, or resume an interrupted run
    python categorize_feedback_scale.py --limit 5  # only the first 5 reviews
    python categorize_feedback_scale.py --fresh    # start over
"""

from typing import Literal

from pydantic import BaseModel

from common.ai_client import ask
from common.reviews import review_prompt, run_per_review

INSTRUCTIONS = """\
You rate restaurant feedback on a five-point scale.
Weigh the written feedback together with the star rating. When the two
disagree, trust what the customer wrote.
Give the reason for your choice in one short sentence."""


class FeedbackScale(BaseModel):
    scale: Literal["Great", "Good", "Neutral", "Bad", "Terrible"]
    reason: str


def categorize(review: dict) -> list[dict]:
    answer = ask(INSTRUCTIONS, review_prompt(review), FeedbackScale)
    return [{"feedback_scale": answer.scale, "feedback_scale_reason": answer.reason.strip()}]


if __name__ == "__main__":
    run_per_review(__doc__, "feedback_scale.csv", ["feedback_scale", "feedback_scale_reason"], categorize)
