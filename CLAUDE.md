# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

MediaSort is a Flask web app for sorting smartphone/DSLR photos and videos into folders. It scans an input directory, extracts EXIF metadata, stores rows in SQLite, groups items client-side by time gap, and lets users name/split/delete sets before moving them to output directories.

## Environment

The project uses direnv with `layout python3`. On first use:

```bash
direnv allow
pip install -r requirements.txt
```

Environment variables (`FLASK_DEBUG`, `FLASK_DB_PATH`, `FLASK_GEOAPIFY_API_KEY`) are set via `.envrc`.

## Commands

```bash
# Run dev server (local)
python3 -m flask --app web_app run

# Run dev server (network-visible)
python3 -m flask --app web_app run --host=0.0.0.0

# Docker
docker-compose -f docker-compose.yml up   # app at http://localhost:8000

# Tests
python3 -m pytest
python3 -m pytest tests/test_api.py::test_name   # single test
python3 -m pytest --cov . --cov-branch --cov-report html

# Format / lint
python3 -m black .
python3 -m flake8
```

`exiftool` must be installed and at version ≥ 12.15 or media-parsing tests will fail.

## Architecture

### Core domain (root)
- **`MediaItem.py`** — Single media file: EXIF extraction (exifread + ExifTool fallback), GPS parsing, file-move with collision detection.
- **`MediaSet.py`** — Two classes: `MediaSet` (lightweight time-boundary tracker) and `MediaSetStore` (holds actual items, bulk move/delete, output-path generation).
- **`MediaFiles.py`** — Recursive generator of media file paths from a directory.

### Flask app (`web_app/`)
- **`__init__.py`** — Application factory `create_app()`. Config loads in this order: env vars → `default_config.py` → `default_config_dev.py` (when `DEBUG=true`) → env vars again → explicit `config_map` passed to `create_app()`.
- **`db.py`** — SQLite connection lifecycle and schema. Schema tables: `items`, `suggestions`, `location_cache`, `meta`. No migrations — only initial `init_db()`.
- **`data.py`** — Data access and orchestration: `populate_db()` scans input dir in a background thread; `move_items()` performs the actual file moves; suggestion and location-cache helpers.
- **`api.py`** — JSON REST endpoints: `GET /api/status`, `GET /api/items` (cursor-based pagination), `POST /api/set/<action>` (actions: `save_date`, `save_no_date`, `delete`), `GET /api/suggestions`, `GET /api/reload`.
- **`ui.py`** — HTML routes: `GET /` renders main UI; `GET /thumbnail/<item_id>` serves thumbnails.
- **`system.py`** — `make_thumbnail()` (Pillow first, ffmpeg fallback); `get_location()` (Geoapify reverse geocoding with SQLite cache, rounds coords to 4 decimals).

### Frontend
`web_app/templates/index.html` is a SPA-style page that fetches paginated items from the API and groups them client-side by configurable time gap (default 2 hours). All set-splitting and naming logic lives in the browser.

### Key config variables
- `FLASK_DB_PATH` — SQLite path (default `mediasort.db`)
- `FLASK_GEOAPIFY_API_KEY` — enables reverse geocoding
- `FLASK_DEBUG=true` — loads dev config
- `DRY_RUN` — default `True`; set `False` to allow actual file moves

### Tests (`tests/`)
Fixtures in `tests/conftest.py`: creates a temporary Flask app via `create_app({...})`, a test SQLite database, and stubs `system.request_location` to avoid Geoapify calls. Always use `create_app()` rather than global app state in tests.

## Development Notes

- All database access must go through `web_app.db.get_db()` inside a Flask app/request context.
- Use parameterized SQL for values. Existing dynamic placeholder lists in `data.py` (generated from integer IDs) are acceptable.
- The "delete" action moves files into a deleted folder — it does not permanently delete them. Be careful with any code path that moves or modifies media files.
- Thumbnail generation tries Pillow first; falls back to ffmpeg for unsupported formats.
- Keep UI changes compatible with `web_app/templates/index.html` client-side grouping logic.
- Do not add real network calls to tests — stub or mock external services.
- Run Black after making broad Python edits.
