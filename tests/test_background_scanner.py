import pytest

import web_app


@pytest.fixture(autouse=True)
def cleanup_scanner_locks():
    yield
    for lock_file in web_app._scanner_locks.values():
        lock_file.close()
    web_app._scanner_locks.clear()


class FakeThread:
    started = []

    def __init__(self, target, daemon, name):
        self.target = target
        self.daemon = daemon
        self.name = name

    def start(self):
        self.started.append(self)


def test_background_scanner_starts_once_per_db(app, monkeypatch):
    monkeypatch.setattr(web_app.threading, "Thread", FakeThread)
    FakeThread.started = []
    app.config["SCAN_INTERVAL_HOURS"] = 2

    first = web_app._start_background_scanner(app)
    second = web_app._start_background_scanner(app)

    assert first is FakeThread.started[0]
    assert second is None
    assert len(FakeThread.started) == 1
