from codetiming import Timer

import logging
import os
import re
import shutil
from datetime import datetime

from flask import current_app

from web_app import db

import MediaFiles
from MediaItem import MediaItem
from web_app import system

STATUS_KEY = "status"


def _set_status(value, conn=None):
    if conn is None:
        conn = db.get_db()
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        (STATUS_KEY, value),
    )
    conn.commit()


def get_status():
    conn = db.get_db()
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (STATUS_KEY,)).fetchone()
    if row is None:
        return None
    return row["value"]


def clear_db():
    message = (
        "*************************** DELETING FROM DB! ***************************"
    )
    logger = logging.getLogger("mediasort.system.clear_db")
    logger.warning(message)

    conn = db.get_db()

    suggestions = []
    locations = []
    if current_app.config.get("KEEP_SUGGESTIONS"):
        suggestions = [
            row["name"] for row in conn.execute("SELECT name FROM suggestions")
        ]
    if current_app.config.get("KEEP_LOCATIONS"):
        locations = [
            (row["lat"], row["lon"], row["location"])
            for row in conn.execute("SELECT lat, lon, location FROM location_cache")
        ]

    if current_app.config.get("FLUSH"):
        logger.warning("Flushing DB")
        conn.execute("DELETE FROM items")
        conn.execute("DELETE FROM suggestions")
        conn.execute("DELETE FROM location_cache")
        conn.execute("DELETE FROM meta")
    else:
        logger.warning("Deleting from DB")
        conn.execute("DELETE FROM items")
        conn.execute("DELETE FROM meta")
        if not current_app.config.get("KEEP_SUGGESTIONS"):
            conn.execute("DELETE FROM suggestions")
        if not current_app.config.get("KEEP_LOCATIONS"):
            conn.execute("DELETE FROM location_cache")

    if current_app.config.get("KEEP_SUGGESTIONS"):
        conn.executemany(
            "INSERT OR IGNORE INTO suggestions (name) VALUES (?)",
            [(name,) for name in suggestions],
        )
    if current_app.config.get("KEEP_LOCATIONS"):
        conn.executemany(
            "INSERT OR REPLACE INTO location_cache (lat, lon, location) VALUES (?, ?, ?)",
            locations,
        )

    conn.commit()


def _lookup_location(conn, coords):
    rounded_coords = round(float(coords[0]), 4), round(float(coords[1]), 4)

    cached = conn.execute(
        "SELECT location FROM location_cache WHERE lat = ? AND lon = ?",
        (rounded_coords[0], rounded_coords[1]),
    ).fetchone()
    if cached is not None:
        return cached["location"]

    result = system.request_location(rounded_coords)
    if result:
        conn.execute(
            "INSERT OR REPLACE INTO location_cache (lat, lon, location) VALUES (?, ?, ?)",
            (rounded_coords[0], rounded_coords[1], result),
        )
    return result


def _item_to_row(item, conn):
    coords = item.get_coords()
    location = ""
    coords_lat = None
    coords_lon = None
    if coords:
        coords_lat, coords_lon = coords
        location = _lookup_location(conn, coords)
    return {
        "id": item.id,
        "path": item.path,
        "timestamp": int(item.timestamp.timestamp()),
        "orig_filename": item.orig_filename,
        "orig_directory": item.orig_directory,
        "coords_lat": coords_lat,
        "coords_lon": coords_lon,
        "location": location,
    }


def populate_db(force=False):
    logger = logging.getLogger("mediasort.system.populate_db")

    def load_data(input_dir):
        db_path = current_app.config.get("DB_PATH")
        conn = db.connect_db(db_path)

        _set_status("loading", conn)

        conn.execute("BEGIN")

        for path in MediaFiles.get_media(input_dir):
            logger.debug(f"Loading path: {path}")
            try:
                item = MediaItem(path)
            except Exception:
                logger.warning(f"Unable to add file: {path}")
                continue

            row = _item_to_row(item, conn)
            conn.execute(
                """
                INSERT OR REPLACE INTO items
                    (id, path, timestamp, orig_filename, orig_directory, coords_lat, coords_lon, location)
                VALUES
                    (:id, :path, :timestamp, :orig_filename, :orig_directory, :coords_lat, :coords_lon, :location)
                """,
                row,
            )

        conn.commit()
        _set_status("done", conn)
        conn.close()

    if current_app.testing:
        load_data(current_app.config.get("INPUT_DIR"))
    else:
        logger.info("Starting new thread for load")
        from flask_executor import Executor

        executor = Executor(current_app)
        executor.submit(load_data, current_app.config.get("INPUT_DIR"))

    return


def get_item_count():
    conn = db.get_db()
    row = conn.execute("SELECT COUNT(*) AS count FROM items").fetchone()
    return row["count"]


def add_suggestion(name):
    conn = db.get_db()
    conn.execute("INSERT OR IGNORE INTO suggestions (name) VALUES (?)", (name,))
    conn.commit()


def get_suggestions():
    conn = db.get_db()
    return [row["name"] for row in conn.execute("SELECT name FROM suggestions")]


def get_item_path(item_id):
    conn = db.get_db()
    row = conn.execute("SELECT path FROM items WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        return None
    return row["path"]


def get_items_by_ids(item_ids):
    if not item_ids:
        return {}

    conn = db.get_db()
    placeholders = ",".join(["?"] * len(item_ids))
    rows = conn.execute(
        f"SELECT * FROM items WHERE id IN ({placeholders})", item_ids
    ).fetchall()
    return {row["id"]: dict(row) for row in rows}


def delete_items(item_ids):
    if not item_ids:
        return

    conn = db.get_db()
    placeholders = ",".join(["?"] * len(item_ids))
    conn.execute(f"DELETE FROM items WHERE id IN ({placeholders})", item_ids)
    conn.commit()


@Timer(name="get_items", text="{name}: {:.4f} seconds")
def get_items(limit=20, after_ts=None, after_id=None, order="asc"):
    conn = db.get_db()

    order_sql = "ASC" if order.lower() != "desc" else "DESC"
    params = []

    where_clause = ""
    if after_ts is not None:
        if order_sql == "ASC":
            where_clause = "WHERE (timestamp > ?) OR (timestamp = ? AND id > ?)"
        else:
            where_clause = "WHERE (timestamp < ?) OR (timestamp = ? AND id < ?)"
        params.extend([after_ts, after_ts, after_id or 0])

    query = (
        "SELECT * FROM items "
        f"{where_clause} "
        f"ORDER BY timestamp {order_sql}, id {order_sql} "
        "LIMIT ?"
    )
    params.append(limit + 1)

    rows = conn.execute(query, params).fetchall()

    has_more = len(rows) > limit
    rows = rows[:limit]

    items = [dict(row) for row in rows]
    next_after = None
    if items:
        last = items[-1]
        next_after = {"timestamp": last["timestamp"], "id": last["id"]}

    return items, next_after, has_more


def _sanitize_name(name):
    return re.sub(r"[^\w &-]+", "", name).strip()


def _date_directory(ts):
    return datetime.fromtimestamp(ts).strftime("%Y/%Y-%m/%Y-%m-%d").strip()


def _move_path(path, directory, dry_run=False):
    orig_filename = os.path.basename(path)
    base, ext = os.path.splitext(orig_filename)
    dest_filename = orig_filename
    counter = None

    while os.path.exists(os.path.join(directory, dest_filename)):
        counter = 0 if counter is None else counter + 1
        dest_filename = f"{base}-{counter:04d}{ext}"

    dest = os.path.join(directory, dest_filename)
    logging.getLogger("mediasort.data.move").info(f"{path} > {dest}")

    if dry_run:
        return

    shutil.move(path, dest)


def move_items(action, item_ids, name=None, dry_run=False):
    logger = logging.getLogger("mediasort.data.move_items")

    items_by_id = get_items_by_ids(item_ids)
    if not items_by_id:
        raise ValueError("No items found")

    timestamps = [items_by_id[item_id]["timestamp"] for item_id in item_ids]
    start_ts = min(timestamps)

    if "save" in action:
        if not name:
            raise ValueError("You must provide a name to save")
        name = _sanitize_name(name)
        if not name:
            raise ValueError("You must provide a name to save")

    if action == "save_date":
        directory = os.path.join(
            current_app.config.get("OUTPUT_DIR"),
            f"{_date_directory(start_ts)} {name}",
        )
    elif action == "save_no_date":
        directory = os.path.join(current_app.config.get("OUTPUT_DIR"), name)
    elif action == "delete":
        directory = current_app.config.get("DELETE_DIR")
    else:
        raise ValueError("Unknown action")

    if not dry_run:
        os.makedirs(directory, exist_ok=True)
    else:
        logger.info(
            "Moving files in dry_run mode! No changes will occur to the file system."
        )

    for item_id in item_ids:
        path = items_by_id[item_id]["path"]
        _move_path(path, directory, dry_run)

    delete_items(item_ids)

    return directory
