"""Thin wrapper around the OpenAI SDK used by every categorize_*.py script."""

from functools import lru_cache
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from common.config import settings

ResponseModel = TypeVar("ResponseModel", bound=BaseModel)

EMBEDDING_BATCH_SIZE = 100


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    if not settings.openai_api_key:
        raise SystemExit("OPENAI_API_KEY is not set. Copy .env.example to .env and add your key.")
    # The SDK retries rate limits and network blips on its own, with exponential backoff.
    return OpenAI(api_key=settings.openai_api_key, max_retries=5)


def ask(instructions: str, content: str, response_model: type[ResponseModel]) -> ResponseModel:
    """Send one prompt and get the answer back as a validated `response_model`.

    Structured Outputs forces the model to answer in the exact shape of the
    Pydantic class, so there is no free-text reply to split or clean up.
    """
    completion = get_client().chat.completions.parse(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": content},
        ],
        response_format=response_model,
    )
    message = completion.choices[0].message
    if message.parsed is None:
        raise RuntimeError(f"The model declined to answer: {message.refusal}")
    return message.parsed


def embed(texts: list[str]) -> list[list[float]]:
    """Turn each text into an embedding vector. Texts that mean similar things get similar vectors."""
    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[start : start + EMBEDDING_BATCH_SIZE]
        response = get_client().embeddings.create(model=settings.openai_embedding_model, input=batch)
        vectors.extend(item.embedding for item in response.data)
    return vectors
