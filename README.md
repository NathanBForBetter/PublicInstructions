# AI Categories with Python, OpenAI and PostgreSQL

A hands-on starter project for anyone who wants to get comfortable with three
things at once: writing Python, calling an AI model from code, and analyzing
the results with SQL.

You start with a CSV of restaurant reviews. Five small Python scripts ask an
OpenAI model to categorize those reviews in different ways, and five more load
the results into PostgreSQL and answer questions about them.

```
data/sample_restaurant_feedback.csv        50 made-up reviews (or your own file)
        |
        |   categorize_*.py                one OpenAI call per review
        v
output/*.csv                               one CSV per kind of category
        |
        |   analyze_*.py                   bulk-load with COPY, then query
        v
PostgreSQL schema "ai_categories"          results printed in your terminal
```

## Contents

1. [Install VS Code and Python](#1-install-vs-code-and-python)
2. [Get the code and install the dependencies](#2-get-the-code-and-install-the-dependencies)
3. [Check that Python works](#3-check-that-python-works)
4. [Configure your `.env` file](#4-configure-your-env-file)
5. [Part 1: Categorize reviews with AI](#5-part-1-categorize-reviews-with-ai)
6. [Part 2: Analyze the categories in PostgreSQL](#6-part-2-analyze-the-categories-in-postgresql)
7. [Project layout](#7-project-layout)
8. [Troubleshooting](#8-troubleshooting)

## 1. Install VS Code and Python

1. Install [Visual Studio Code](https://code.visualstudio.com/download).
2. Install [Python](https://www.python.org/downloads/) 3.10 or newer.
3. In VS Code, install the
   [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python).
4. Create a folder to hold all of your development projects, for example
   `PythonProjects` in your home folder. The rest of this guide calls it your
   base dev folder.

## 2. Get the code and install the dependencies

Clone this repository into your base dev folder, then open the new
`PublicInstructions` folder in VS Code (**File > Open Folder**).

```bash
git clone https://github.com/NathanBForBetter/PublicInstructions.git
```

Create a virtual environment so the packages this project needs stay separate
from the rest of your computer:

1. Open the Command Palette with `Shift` + `Cmd` + `P` (Mac) or
   `Ctrl` + `Shift` + `P` (Windows).
2. Type and select **Python: Create Environment**.
3. Select **Venv**, then pick your Python version.
4. When VS Code asks which dependencies to install, tick `requirements.txt`.

VS Code creates a `.venv` folder and uses it automatically from then on. See
[Python environments in VS Code](https://code.visualstudio.com/docs/python/environments)
if anything looks different on your machine.

Prefer the terminal? This does the same thing:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Check that Python works

1. In VS Code's file explorer (top-left icon), create a file called `test.py`.
2. Paste in this line:

   ```python
   print("hell yeah I made a python file and ran it!")
   ```

3. Press the play button in the upper-right corner.

The text appears in the terminal panel at the bottom of VS Code. You can delete
`test.py` afterwards.

## 4. Configure your `.env` file

API keys, passwords and file paths do not belong in code, so every script reads
them from a file called `.env`. Create yours by copying the example:

```bash
cp .env.example .env
```

`.env` is listed in `.gitignore`, so it is never committed. Open it and fill in
the values:

| Variable | What it is | Default |
| --- | --- | --- |
| `OPENAI_API_KEY` | Your secret key. Create one on the [API keys page](https://platform.openai.com/api-keys). API usage is billed separately from a ChatGPT subscription. | none, required for Part 1 |
| `OPENAI_MODEL` | The chat model that does the categorizing. Any [model](https://developers.openai.com/api/docs/models) that supports Structured Outputs works. | `gpt-6-luna` |
| `OPENAI_EMBEDDING_MODEL` | The embedding model, only used by `categorize_feedback_themes.py`. | `text-embedding-3-small` |
| `INPUT_CSV_PATH` | The reviews to categorize. | `data/sample_restaurant_feedback.csv` |
| `OUTPUT_DIR` | The folder the category CSVs are written to. | `output` |
| `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` | Where your PostgreSQL server is. The defaults match a standard local install. | `localhost`, `5432`, `postgres`, `postgres` |
| `PGPASSWORD` | The password you chose when installing PostgreSQL. | none, required for Part 2 |

Relative paths are resolved from the repository root. Absolute paths and `~`
work too.

## 5. Part 1: Categorize reviews with AI

Each script reads the reviews, asks the model one focused question, and appends
the answers to its own CSV in `output/`.

| Script | What it adds | Output CSV |
| --- | --- | --- |
| `categorize_feedback_emotion.py` | Up to five emotions per review, strongest first. | `feedback_emotions.csv` |
| `categorize_feedback_scale.py` | One rating per review from a fixed scale (Great, Good, Neutral, Bad, Terrible), with a one-sentence reason. | `feedback_scale.csv` |
| `categorize_restaurant_type.py` | One type per restaurant, such as "sushi". Types already used are fed back to the model so labels stay consistent. | `restaurant_types.csv` |
| `categorize_feedback_aspects.py` | Aspect-based sentiment: a separate sentiment for food, service, price, ambiance, wait time and cleanliness, each backed by a quote from the review. | `feedback_aspects.csv` |
| `categorize_feedback_themes.py` | Themes nobody defined in advance: reviews are embedded, clustered with k-means, and each cluster is named by the model. | `feedback_themes.csv` |

### Run your first categorization

Start with a handful of reviews to confirm that your key works:

```bash
python categorize_feedback_scale.py --limit 5
```

You should see one line per review as it is categorized, and the results in
`output/feedback_scale.csv`. Then run it without `--limit`, and run the other
scripts the same way. The play button works too; it runs the script on the
whole input file.

The categorize scripts share these options:

| Option | Effect |
| --- | --- |
| `--limit N` | Only read the first `N` reviews. |
| `--fresh` | Discard the existing output CSV and start over. |
| `--help` | Show what the script does and its options. |

Rows are appended to the CSV after every AI call. If a run is interrupted, run
the same command again: reviews that are already in the CSV are skipped rather
than sent to the model a second time.

`categorize_feedback_themes.py` is the exception. Its themes depend on all the
reviews together, so it rebuilds its CSV on every run and has no `--fresh`
option. It takes `--themes N` instead, to set the number of themes yourself.

As a rough estimate from OpenAI's list prices, running all five scripts on the
50 sample reviews should cost a few cents with the default model. See
[OpenAI's pricing](https://developers.openai.com/api/docs/pricing) for current
rates.

### How the scripts get reliable answers

Asking a model to "just reply with one category" works most of the time, and
then one day it replies with a full sentence and breaks your CSV. These scripts
use [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
instead. Each one describes the answer it wants as a small class, and the model
is required to answer in exactly that shape:

```python
class FeedbackScale(BaseModel):
    scale: Literal["Great", "Good", "Neutral", "Bad", "Terrible"]
    reason: str
```

The two newer scripts go a step further:

- **`categorize_feedback_aspects.py`** makes the model quote the words it based
  each sentiment on, then checks that the quote really appears in the review.
  The result is saved in the `quote_is_verbatim` column, so made-up evidence is
  easy to find.
- **`categorize_feedback_themes.py`** does not ask the model to classify
  anything. It turns each review into an
  [embedding](https://developers.openai.com/api/docs/guides/embeddings), groups
  similar reviews with
  [k-means clustering](https://scikit-learn.org/stable/modules/clustering.html#k-means),
  and only then asks the model to name each group. The `theme_fit` column shows
  how typical each review is of its theme (1.0 is a perfect fit).

### Use your own reviews

Point `INPUT_CSV_PATH` in `.env` at any CSV with these columns:

| Column | Required | Notes |
| --- | --- | --- |
| `restaurant_feedback` | yes | The review text. Rows where it is blank are skipped. |
| `restaurant_name` | yes | |
| `restaurant_rating_out_of_5` | yes | May be blank. `restaurant_rating` is accepted as well. |
| `review_id` | no | A whole number that identifies the review. If the column is missing, the row number is used. |

After switching to a different input file, run each script once with `--fresh`
so results from the old file are not mixed in.

## 6. Part 2: Analyze the categories in PostgreSQL

### Install PostgreSQL

1. Install PostgreSQL for [macOS](https://www.postgresql.org/download/macosx/)
   or [Windows](https://www.postgresql.org/download/windows/). Prisma's guide to
   [setting up a local PostgreSQL database](https://www.prisma.io/dataguide/postgresql/setting-up-a-local-postgresql-database#installing-postgresql-on-macos)
   walks through the installer step by step. The link opens at the macOS
   section, and Windows is covered on the same page.
2. Keep the installer's defaults (host `localhost`, port `5432`, database
   `postgres`, user `postgres`) and choose a password. Those defaults are
   already in `.env.example`, so the password is the only value you need to
   add to `.env`.
3. To browse your tables from VS Code, install the
   [PostgreSQL extension by Chris Kolkman](https://marketplace.visualstudio.com/items?itemName=ckolkman.vscode-postgres)
   and connect with the same values. CommandPrompt's article on
   [connecting to PostgreSQL from VS Code](https://www.commandprompt.com/education/how-to-connect-to-postgresql-from-visual-studio-code/)
   shows the connection steps, but the extension it recommends no longer works,
   so use the one linked here.

This database only exists on your computer, so you can experiment freely.

### Run an analysis

Each analysis script loads the CSVs it needs into tables, runs a few queries,
and prints the results. Each one is built around a different SQL technique, and
the queries are written out in full at the top of the file with comments.

| Script | Needs the CSV from | SQL techniques | Questions it answers |
| --- | --- | --- | --- |
| `analyze_sentiment_summary.py` | `categorize_feedback_scale.py` | [Aggregates](https://www.postgresql.org/docs/current/sql-expressions.html#SYNTAX-AGGREGATES): `GROUP BY`, `FILTER`, `HAVING`, `CASE` | What is each restaurant's mix of sentiment? Who has repeated complaints? Where do the stars and the AI disagree? |
| `analyze_emotion_rankings.py` | `categorize_feedback_emotion.py` | [Window functions](https://www.postgresql.org/docs/current/tutorial-window.html): `ROW_NUMBER`, `DENSE_RANK`, running totals | What are the top emotions per restaurant, overall, and for happy vs. unhappy customers? |
| `analyze_restaurant_benchmarks.py` | `categorize_restaurant_type.py` and `categorize_feedback_scale.py` | Joins and [CTEs](https://www.postgresql.org/docs/current/queries-with.html): `JOIN`, `FULL OUTER JOIN`, `WITH` | How does each restaurant compare with others of its type? Which types rate best? |
| `analyze_aspect_scorecard.py` | `categorize_feedback_aspects.py` | Pivoting: temporary views, [`GROUPING SETS`](https://www.postgresql.org/docs/current/queries-table-expressions.html#QUERIES-GROUPING-SETS), `DISTINCT ON` | What is each restaurant's strongest and weakest aspect? Which evidence quotes could not be verified? |
| `analyze_theme_search.py` | `categorize_feedback_themes.py` | [Full-text search](https://www.postgresql.org/docs/current/textsearch.html): `tsvector`, GIN index, `ts_rank`, `ts_headline` | Which reviews mention a phrase, and which themes do they belong to? |

```bash
python analyze_sentiment_summary.py
```

`analyze_theme_search.py` takes the text to look for, with the same syntax as a
web search box:

```bash
python analyze_theme_search.py --search '"hung up" OR rude -burger'
```

### Where the tables live

The scripts create their tables in a separate schema called `ai_categories`,
so they never touch tables you already have. Every run drops and reloads the
tables it uses, which means the database always matches your CSVs.

To explore the tables yourself, include the schema name:

```sql
SELECT * FROM ai_categories.feedback_scale LIMIT 10;
```

To remove everything this project created:

```sql
DROP SCHEMA ai_categories CASCADE;
```

## 7. Project layout

```
PublicInstructions/
├── .env.example                        template for your own .env
├── requirements.txt                    Python packages
├── data/
│   └── sample_restaurant_feedback.csv  50 made-up reviews of 10 made-up restaurants
├── common/                             code shared by the scripts
│   ├── config.py                       reads .env
│   ├── ai_client.py                    OpenAI calls: structured answers and embeddings
│   ├── reviews.py                      reads the input CSV, appends to output CSVs, resumes runs
│   └── database.py                     PostgreSQL connection, table definitions, COPY loading
├── categorize_feedback_emotion.py      Part 1
├── categorize_feedback_scale.py
├── categorize_restaurant_type.py
├── categorize_feedback_aspects.py
├── categorize_feedback_themes.py
├── analyze_sentiment_summary.py        Part 2
├── analyze_emotion_rankings.py
├── analyze_restaurant_benchmarks.py
├── analyze_aspect_scorecard.py
└── analyze_theme_search.py
```

The `output/` folder is created the first time you run a categorize script. It
is ignored by git, like `.env` and `.venv/`.

## 8. Troubleshooting

| Message | Fix |
| --- | --- |
| `OPENAI_API_KEY is not set` | Create `.env` from `.env.example` and add your key ([step 4](#4-configure-your-env-file)). |
| `ModuleNotFoundError: No module named ...` | The virtual environment is not active, or the packages are not installed. Repeat [step 2](#2-get-the-code-and-install-the-dependencies). |
| An OpenAI error saying the model does not exist or you do not have access | Set `OPENAI_MODEL` in `.env` to a model your account can use. |
| An OpenAI error about quota or billing | Add credit to your OpenAI account. API usage is not included in a ChatGPT subscription. |
| `... has different columns than this script writes` | The output CSV comes from an older version of the script. Rerun with `--fresh`. |
| `Could not connect to PostgreSQL` | Check that PostgreSQL is running and that the `PG*` values in `.env` match your install. |
| `... .csv not found. Run ... first` | Run the categorize script named in the message, then rerun the analysis. |
