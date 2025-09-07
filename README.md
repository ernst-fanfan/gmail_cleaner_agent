# Gmail Smart Cleaner

Daily Gmail triage with safety rails, rules, and an optional LLM to reduce inbox noise. Runs at 22:00 and emails a Markdown report.

- Plan: see `PLAN.md`
- Testing plan: see `PLAN-TESTING.md`
- Config template: `config.example.yaml`

**Python 3.13** is required for local runs; Docker images also use 3.13.

**Secret hygiene**: `config.yaml`, `data/` (Google creds/tokens, SQLite), and `reports/` are gitignored and excluded from Docker build via `.dockerignore`.

**Default safety**: dry-run mode and no permanent deletes by default.

**Compose-first workflow** below is recommended.

**Local (optional)**
- Create a venv and install: `pip install -e .[dev]`
- One-off dry run: `python -m cleanmail.main run --dry-run`

**Docker Compose (recommended)**
- Copy config: `cp config.example.yaml config.yaml` and edit values.
- Place Google OAuth client at `data/google/credentials.json` (Desktop client from Google Cloud). `token.json` is created on first auth.
- Export your API key: `export OPENAI_API_KEY=...` (if using LLM).

Common commands:
- Build images: `docker compose build`
- Start scheduler service: `docker compose up cleanmail`
- One-off dry run: `docker compose run --rm cleanmail python -m cleanmail.main run --dry-run`
- Run tests (Compose): `docker compose up --build tests` (or `docker compose run --rm tests`)
- Dev shell (for pytest/CLI):
  - Start: `docker compose up -d dev`
  - Exec: `docker compose exec dev bash`

Testing:
- With Compose: `docker compose up --build tests`
  - With coverage: `docker compose run --rm tests pytest --cov=src/cleanmail --cov-report=term-missing`
- In dev container: `pytest -q`
- Locally (venv): `pip install -e .[dev] && pytest -q`

Mounted volumes (for both services):
- `./src -> /app/src` (live code edits)
- `./prompts -> /app/prompts`
- `./config.yaml -> /app/config.yaml` (read-only)
- `./data -> /app/data` (Google credentials, token, sqlite)
- `./reports -> /app/reports` (generated Markdown reports)

Environment variables:
- `TZ` (defaults to `America/New_York` via compose; set your timezone)
- `OPENAI_API_KEY` (leave empty to disable LLM calls for now)

Healthcheck:
- `docker compose ps` shows health; underlying command runs `python -m cleanmail.main healthcheck`.

Project entrypoints:
- Serve (scheduler): `python -m cleanmail.main serve`
- Run once: `python -m cleanmail.main run`
- Healthcheck: `python -m cleanmail.main healthcheck`

Reports:
- Saved to `reports/YYYY-MM-DD.md` and can be emailed (Gmail send stubbed until Gmail client is implemented).

Notes:
- Do not commit `config.yaml` or anything under `data/` or `reports/`.
- For first-time Gmail auth inside the container, you’ll be prompted to authorize; we’ll wire a headless flow next.

Docker (direct)
- Build image: `docker build -t cleanmail:local .`
- One-off dry run:
  - `docker run --rm \
      -e TZ=${TZ:-America/New_York} \
      -e OPENAI_API_KEY=${OPENAI_API_KEY:-} \
      -v "$PWD/config.yaml:/app/config.yaml:ro" \
      -v "$PWD/data:/app/data" \
      -v "$PWD/reports:/app/reports" \
      cleanmail:local \
      python -m cleanmail.main run --dry-run`
- Scheduler/service:
  - same as above but replace the command with `python -m cleanmail.main serve`

Dependency note
- The Docker image installs dependencies from `pyproject.toml` via `pip install .` — no requirements.txt is needed.

Makefile shortcuts
- `make build` — build local image (`cleanmail:local`)
- `make run-dry` — one-off dry run with volumes mounted
- `make run-serve` — run the scheduler service
- `make compose-build` — build via Docker Compose
- `make compose-up` — start the compose service
- `make compose-dev` — start dev container; `make dev-sh` to open a shell
- `make test` — run tests using the compose tests service
