from web_app import system


def test_thumbnail():
    thumbnail = system.make_thumbnail("images/leaf.jpg")

    assert len(thumbnail) > 7000 and len(thumbnail) < 10000


def test_location(monkeypatch, app):
    def fake_request(coords):
        return "Buckingham Palace"

    with app.app_context():
        monkeypatch.setattr(system, "request_location", fake_request)
        location = system.get_location((51.50084130000768, -0.14298782563424842))

    assert location == "Buckingham Palace"


def test_location_nothing(monkeypatch, app):
    def fake_request(coords):
        return ""

    with app.app_context():
        monkeypatch.setattr(system, "request_location", fake_request)
        location = system.get_location((50, 0))  # In the English Channel

    assert location == ""
