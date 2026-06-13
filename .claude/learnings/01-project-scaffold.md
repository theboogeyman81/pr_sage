# Learnings: 01-Project-Scaffold

---

## pyproject.toml

**`[build-system]`**
- Tells pip HOW to build/install your project
- `hatchling` is the tool that does the actual packaging
- Old way was `setup.py` (a Python script) — pyproject.toml is the modern replacement

**`[project] dependencies` vs `[project.optional-dependencies]`**
- `dependencies` = always installed (your app needs these to run)
- `optional-dependencies` = only installed when you ask for them
- `pip install -e ".[dev]"` — the `[dev]` part is what installs the optional dev group
- Without `[dev]`, you only get fastapi + uvicorn — which is all a production server needs

**`pip install -e ".[dev]"` — what `-e` means**
- `-e` = editable install
- Your code is NOT copied into site-packages — pip just points there to your folder
- So when you edit a file, the change is live instantly. No reinstall needed.

**`packages = ["app"]` under `[tool.hatch.build.targets.wheel]`**
- Hatchling by default looks for a folder named after your project (`pr_sage`)
- Our folder is named `app/` — so we have to tell it explicitly
- This was the one thing that broke during setup and had to be fixed

**`==` pinning (e.g. `fastapi==0.115.6`)**
- Means "exactly this version, nothing else"
- Every machine gets the same version → no surprise breakage
- Downside: you have to manually bump versions to get updates

**`testpaths = ["tests"]`**
- Without this, pytest scans your whole project including `.venv/` (thousands of files)
- This tells pytest to only look in `tests/` — faster and cleaner

---

## app/logging_config.py

**Why it's a separate file**
- Logging is global state — it affects everything
- Keeping it in its own file makes it easy to find and change in one place

**`root.handlers.clear()`**
- uvicorn already sets up its own logging when it starts
- If you don't clear first, you get duplicate log lines (one from uvicorn, one from yours)
- Always clear before adding your own handler

**`logging.getLogger()` with no args**
- Returns the ROOT logger — the parent of all other loggers
- Any logger you create in other files (`getLogger(__name__)`) is a child of root
- Children inherit root's handler, so your format applies everywhere automatically

**`datetime.now(timezone.utc)` instead of `datetime.utcnow()`**
- `utcnow()` gives you a time with no timezone info attached — ambiguous
- `datetime.now(timezone.utc)` gives `2026-06-12T13:46:27+00:00` — clearly UTC
- `utcnow()` was also deprecated in Python 3.12 so avoid it

**`record.getMessage()` not `record.msg`**
- `record.msg` is the raw string before args are filled in: `"user %s logged in"`
- `record.getMessage()` fills in the args: `"user alice logged in"`
- Always use `getMessage()` in a custom formatter

**`_KeyValueFormatter` — the underscore prefix**
- `_` before a name = "private, don't use this outside this file"
- It's just a convention but a useful signal to anyone reading the code

**Why `configure_logging()` is called at the top of `main.py` (not in a startup event)**
- FastAPI has startup hooks but they run after import
- If any code logs during import, you'd miss it
- Calling it at the top of `main.py` means it runs first, before anything else

---

## app/main.py

**`app.include_router(health_router)`**
- Instead of defining all routes in `main.py`, you define them in separate files (routers)
- `main.py` just collects and registers them all
- Keeps `main.py` clean as the app grows — you'd add one line per new feature

---

## app/routes/health.py

**`logging.getLogger(__name__)`**
- `__name__` is automatically the full module name: `app.routes.health`
- So your log line says `logger=app.routes.health` — you know exactly where it came from
- Standard pattern — use it in every file that logs

**`-> dict[str, str]` return type**
- FastAPI reads this to validate your response and generate the `/docs` page automatically
- If you return the wrong type, FastAPI raises a 500 before sending anything to the client
- `dict[str, str]` = a dictionary where both keys and values are strings

---

## tests/test_health.py

**`TestClient` — what it does**
- Runs your FastAPI app in-process (no real server, no port)
- You call `.get("/health")` and it goes through your actual app code and comes back
- Fast and reliable — no network involved

**Why `httpx` is in dev deps even though you never import it**
- `TestClient` uses httpx internally — it's a hidden dependency
- If httpx isn't installed, importing `TestClient` fails

**Why assert BOTH status code and body**
```python
assert response.status_code == 200
assert response.json() == {"status": "ok"}
```
- Status only: a 200 with `{"error": "something broke"}` would pass — bad
- Body only: doesn't catch the case where you accidentally return a 201 or 404
- Both together = the full contract is tested

---

## Project structure

**`__init__.py` files (empty)**
- Tell Python "this folder is a package you can import from"
- Without them, `from app.main import app` would fail
- They're empty — just need to exist

**`.env.example` committed, `.env` gitignored**
- `.env` has real secrets (tokens, passwords) — never commit it
- `.env.example` shows WHAT variables are needed, with empty values — safe to commit
- New developer workflow: `cp .env.example .env` then fill in real values

**Why `routes/` is its own subfolder**
- Right now it only has `health.py`
- When you add webhook handling, PR review, etc. — each gets its own file here
- Keeps things organized from the start instead of having to reorganize later
