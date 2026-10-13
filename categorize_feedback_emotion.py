"""Tag every review with up to five emotions, strongest first.

Appends one row per emotion to feedback_emotions.csv in the output folder.

    python categorize_feedback_emotion.py            # run, or resume an interrupted run
    python categorize_feedback_emotion.py --limit 5  # only the first 5 reviews
    python categorize_feedback_emotion.py --fresh    # start over
"""

from pydantic import BaseModel

from common.ai_client import ask
from common.reviews import review_prompt, run_per_review

MAX_EMOTIONS = 5

INSTRUCTIONS = f"""\
You label the emotions a customer expresses in restaurant feedback.
Consider both the written feedback and the star rating.
Return between one and {MAX_EMOTIONS} distinct emotions, strongest first.
Each emotion is one or two lowercase words, such as "delighted" or "let down"."""


class FeedbackEmotions(BaseModel):
    emotions: list[str]


def categorize(review: dict) -> list[dict]:
    answer = ask(INSTRUCTIONS, review_prompt(review), FeedbackEmotions)
    cleaned = [emotion.strip().lower() for emotion in answer.emotions if emotion.strip()]
    emotions = list(dict.fromkeys(cleaned))[:MAX_EMOTIONS]  # drop repeats, keep the model's order
    return [{"emotion": emotion, "emotion_rank": rank} for rank, emotion in enumerate(emotions, start=1)]


if __name__ == "__main__":
    run_per_review(__doc__, "feedback_emotions.csv", ["emotion", "emotion_rank"], categorize)
