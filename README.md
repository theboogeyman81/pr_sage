# pr_sage

AI-powered pull request review assistant built on FastAPI and GitHub Apps.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in your values
```

## Run

```bash
uvicorn app.main:app --reload
```

## Test

```bash
pytest
```
