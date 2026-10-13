"""Discover recurring themes across all reviews, without defining categories up front.

The other scripts ask the model to choose from labels we thought of in advance.
This one works bottom-up:

1. Embeddings turn every review into a vector. Reviews that mean similar things
   get similar vectors.
2. K-means groups the vectors into clusters. Unless you pass --themes, the
   number of clusters is the one with the best silhouette score.
3. The model reads the most typical reviews of each cluster and names the theme.

Themes depend on the whole set of reviews, so every run rebuilds
feedback_themes.csv in the output folder, appending one theme at a time.

    python categorize_feedback_themes.py             # choose the number of themes automatically
    python categorize_feedback_themes.py --themes 4  # find exactly 4 themes
    python categorize_feedback_themes.py --limit 20  # only the first 20 reviews
"""

import numpy as np
from pydantic import BaseModel
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from common.ai_client import ask, embed, get_client
from common.config import settings
from common.reviews import REVIEW_COLUMNS, OutputCsv, cli_parser, load_reviews

MAX_THEMES = 8
TYPICAL_REVIEWS = 5
RANDOM_SEED = 0  # the same reviews always produce the same clusters

INSTRUCTIONS = """\
These restaurant reviews were grouped together because they are about similar things.
Name the theme they share in two to four words and describe it in one sentence.
Focus on what the reviews have in common, not on any single restaurant.
Do not reuse a theme name that is already taken."""


class Theme(BaseModel):
    name: str
    description: str


def unit_length(vectors: np.ndarray) -> np.ndarray:
    """Scale every vector to length 1, so the dot product of two vectors is their cosine similarity."""
    return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def cluster(vectors: np.ndarray, theme_count: int | None) -> KMeans:
    """Group the vectors with k-means, trying several cluster counts if none was asked for."""

    def fit(count: int) -> KMeans:
        return KMeans(n_clusters=count, n_init=10, random_state=RANDOM_SEED).fit(vectors)

    if theme_count:
        return fit(theme_count)
    # The silhouette score is high when clusters are tight and far apart from each other.
    candidates = [fit(count) for count in range(2, min(MAX_THEMES, len(vectors) - 1) + 1)]
    return max(candidates, key=lambda model: silhouette_score(vectors, model.labels_))


def name_theme(typical_feedback: list[str], taken_names: list[str]) -> Theme:
    content = "\n".join(
        [
            f"Theme names already taken: {', '.join(taken_names) or 'none yet'}",
            "Reviews:",
            *[f"- {feedback}" for feedback in typical_feedback],
        ]
    )
    return ask(INSTRUCTIONS, content, Theme)


def main() -> None:
    parser = cli_parser(__doc__, resumable=False)
    parser.add_argument("--themes", type=int, help="number of themes to find (default: chosen automatically)")
    args = parser.parse_args()
    get_client()  # stop right away if the API key is missing

    reviews = load_reviews(args.limit)
    if len(reviews) < 3:
        raise SystemExit("Theme discovery needs at least 3 reviews.")
    if args.themes is not None and not 1 <= args.themes <= len(reviews):
        raise SystemExit(f"--themes must be between 1 and the number of reviews ({len(reviews)}).")

    print(f"Embedding {len(reviews)} reviews with {settings.openai_embedding_model}...")
    vectors = unit_length(np.array(embed(reviews["restaurant_feedback"].tolist())))

    model = cluster(vectors, args.themes)
    centers = unit_length(model.cluster_centers_)
    reviews["theme_id"] = model.labels_ + 1
    # How close a review sits to the centre of its own theme: 1.0 is dead centre.
    reviews["theme_fit"] = (vectors * centers[model.labels_]).sum(axis=1).round(3)

    columns = REVIEW_COLUMNS + ["theme_id", "theme", "theme_description", "theme_fit"]
    output = OutputCsv("feedback_themes.csv", columns, fresh=True)
    print(f"Naming {model.n_clusters} themes with {settings.openai_model} -> {output.path}")

    taken_names: list[str] = []
    for theme_id, members in reviews.groupby("theme_id"):
        members = members.sort_values("theme_fit", ascending=False)
        theme = name_theme(members["restaurant_feedback"].head(TYPICAL_REVIEWS).tolist(), taken_names)
        name = theme.name.strip()
        if name in taken_names:  # the model reused a name anyway, so make it unique ourselves
            name = f"{name} ({theme_id})"
        taken_names.append(name)
        output.append(
            [
                {**row, "theme": name, "theme_description": theme.description.strip()}
                for row in members.to_dict("records")
            ]
        )
        print(f"Theme {theme_id}: {name} ({len(members)} reviews) - {theme.description}")

    print(f"Done. Results are in {output.path}")


if __name__ == "__main__":
    main()
