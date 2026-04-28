# AGENTS.md

Guidance for Codex and other coding agents working in this repository.

## Project Overview

MediaSort is a Python 3 Flask app for sorting photo and video files into folders. It scans an input directory, extracts media metadata, stores item rows in SQLite, groups items client-side in the web UI, and moves selected sets into output or deleted folders.

Important modules:

- `web_app/__init__.py`: Flask application factory and config loading.
- `web_app/api.py`: JSON API routes for status, reload, item pagination, suggestions, and set actions.
- `web_app/ui.py`: HTML routes and thumbnail serving.
- `web_app/data.py`: SQLite data access, media scan orchestration, suggestions, and item moving.
- `web_app/db.py`: SQLite connection lifecycle and schema setup.
- `web_app/system.py`: thumbnail generation, ffmpeg/Pillow integration, and Geoapify reverse geocoding.
- `MediaItem.py`, `MediaFiles.py`, `MediaSet.py`: core media parsing and grouping/domain behavior.
- `tests/`: pytest suite with Flask fixtures in `tests/conftest.py`.

## Local State

The worktree may already contain user changes. Before editing, check `git status --short` and avoid reverting unrelated changes.

At initialization time, the following files were already modified:

- `README.md`
- `default_config.py`
- `default_config_dev.py`
- `requirements.txt`
- `tests/test_system.py`
- `web_app/system.py`

Treat those as user-owned unless the current task specifically asks to modify them.

## Running The App

Development server:

```bash
python3 -m flask --app web_app run
```

Network-visible development server:

```bash
python3 -m flask --app web_app run --host=0.0.0.0
```

Docker:

```bash
docker-compose -f docker-compose.yml up
```

The app defaults to port `8000` in Docker and Flask defaults to `5000` locally unless overridden.

## Configuration

Config is loaded in this order:

1. `FLASK_*` environment variables, to detect debug mode early.
2. `default_config.py`.
3. `default_config_dev.py` when `DEBUG` is true.
4. `FLASK_*` environment variables again, to override file defaults.
5. Explicit `config_map` values passed to `create_app()`.

Common variables:

- `FLASK_DB_PATH`: SQLite path, defaults to `mediasort.db` when not overridden.
- `FLASK_GEOAPIFY_API_KEY`: enables reverse geocoding; tests stub external lookups.
- `FLASK_DEBUG=true`: enables dev config.

## Tests And Checks

Primary test command:

```bash
python3 -m pytest
```

Coverage:

```bash
python3 -m pytest --cov . --cov-branch --cov-report html
```

Formatting:

```bash
python3 -m black .
```

Linting:

```bash
python3 -m flake8
```

Tests depend on `exiftool`. Missing or too-old `exiftool` can cause media parsing tests to fail. The README states the minimum version is `12.15`.

## Development Notes

- Prefer existing Flask application factory patterns. Tests should use `create_app({...})` rather than global app state.
- Keep database access through `web_app.db.get_db()` inside app/request contexts.
- Use parameterized SQL for values. Existing dynamic placeholder lists in `data.py` are acceptable when generated from integer IDs.
- Be careful with code paths that move or delete media. The app's delete action moves files into a deleted folder rather than permanently deleting them, but changes can still affect user data.
- In tests, `tests/conftest.py` stubs `system.request_location` to avoid external Geoapify calls.
- Thumbnail generation tries Pillow first and falls back to ffmpeg for unsupported image/video formats.
- Keep UI changes compatible with the server-rendered templates in `web_app/templates/` and the client-side behavior in `web_app/templates/index.html`.

## Style

- Follow the repository's current Python style, then run Black when making broad Python edits.
- Keep changes scoped to the requested behavior.
- Add tests for behavior changes, especially API responses, database mutations, media movement, or config handling.
- Do not add network calls to tests unless explicitly mocked or stubbed.
