import sqlite3
from flask import current_app, g


def connect_db(path):
    conn = sqlite3.connect(
        path, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    return conn


def get_db():
    if "sqlite_db" in g:
        return g.sqlite_db

    db_path = current_app.config.get("DB_PATH")
    g.sqlite_db = connect_db(db_path)
    return g.sqlite_db


def close_db(_=None):
    db = g.pop("sqlite_db", None)
    if db is not None:
        try:
            db.close()
        except sqlite3.ProgrammingError:
            pass


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            timestamp INTEGER NOT NULL,
            orig_filename TEXT NOT NULL,
            orig_directory TEXT NOT NULL,
            coords_lat REAL,
            coords_lon REAL,
            location TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_items_timestamp_id
            ON items (timestamp, id);

        CREATE TABLE IF NOT EXISTS suggestions (
            name TEXT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS location_cache (
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            location TEXT NOT NULL,
            PRIMARY KEY (lat, lon)
        );

        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    db.commit()
