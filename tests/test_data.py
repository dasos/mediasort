from web_app import data

import MediaFiles

LIST_OF_MEDIAITEMS = [
    "images/calculator.jpg",
    "images/dup1/leaf.jpg",
    "images/dup2/leaf.jpg",
    "images/forest.jpg",
    "images/grass-video.mp4",
    "images/leaf.jpg",
    "images/snowy-forest.jpg",
]
LENGTH_OF_MEDIAITEMS = len(LIST_OF_MEDIAITEMS)
LIST_OF_FILES = sorted(["images/not_this"] + LIST_OF_MEDIAITEMS)
LENGTH_OF_FILES = len(LIST_OF_FILES)


def test_find_files():
    l = sorted(list(MediaFiles.get_media("images")))

    assert len(l) == LENGTH_OF_FILES
    assert l == LIST_OF_FILES


def test_load_files():
    items = list(MediaFiles.load("images"))
    assert len(items) == LENGTH_OF_MEDIAITEMS


def test_load_files_db(app):
    with app.app_context():
        data.populate_db()
        assert data.get_item_count() == LENGTH_OF_MEDIAITEMS


def test_get_item_path(app):
    with app.app_context():
        data.populate_db()
        items, _, _ = data.get_items(limit=10000)
        for item in items:
            p1 = item["path"]
            p2 = data.get_item_path(item["id"])
            assert p1 == p2
            assert p1 in LIST_OF_FILES


def test_get_items_pagination(app):
    with app.app_context():
        data.populate_db()
        items, next_after, has_more = data.get_items(limit=3)
        assert len(items) == 3
        assert next_after is not None
        assert has_more is True

        items2, next_after2, has_more2 = data.get_items(
            limit=3,
            after_ts=next_after["timestamp"],
            after_id=next_after["id"],
        )
        assert len(items2) == 3
        assert items2[0]["id"] != items[-1]["id"]
        assert next_after2 is not None
        assert has_more2 in [True, False]


def test_get_items_order(app):
    with app.app_context():
        data.populate_db()
        items, _, _ = data.get_items(limit=10000)
        timestamps = [item["timestamp"] for item in items]
    assert timestamps == sorted(timestamps)


def test_location_populated_on_scan(app, monkeypatch):
    monkeypatch.setattr(
        "web_app.system.request_location", lambda coords: "Address Line 1"
    )

    with app.app_context():
        data.populate_db()
        items, _, _ = data.get_items(limit=10000)

        locations = [item["location"] for item in items if item["location"]]

    assert "Address Line 1" in locations
