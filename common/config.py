"""Settings for every script, read from the .env file in the repo root.

Real environment variables win over .env, so you can override a single value
for one run:  OPENAI_MODEL=gpt-4o python categorize_feedback_scale.py
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(REPO_ROOT / ".env")


def _text(name: str, default: str = "") -> str:
    # A blank line in .env ("PGPASSWORD=") should behave like a missing one.
    return os.getenv(name, "").strip() or default


def _path(name: str, default: str) -> Path:
    path = Path(_text(name, default)).expanduser()
    return path if path.is_absolute() else REPO_ROOT / path


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    openai_embedding_model: str
    input_csv_path: Path
    output_dir: Path
    pg_host: str
    pg_port: int
    pg_database: str
    pg_user: str
    pg_password: str


settings = Settings(
    openai_api_key=_text("OPENAI_API_KEY"),
    openai_model=_text("OPENAI_MODEL", "gpt-6-luna"),
    openai_embedding_model=_text("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    input_csv_path=_path("INPUT_CSV_PATH", "data/sample_restaurant_feedback.csv"),
    output_dir=_path("OUTPUT_DIR", "output"),
    pg_host=_text("PGHOST", "localhost"),
    pg_port=int(_text("PGPORT", "5432")),
    pg_database=_text("PGDATABASE", "postgres"),
    pg_user=_text("PGUSER", "postgres"),
    pg_password=_text("PGPASSWORD"),
)
