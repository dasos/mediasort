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


def test_request_location_uses_address_and_city(monkeypatch, app):
    class FakeResponse:
        status_code = 200
        text = (
            '{"results":[{"address_line1":"1600 Amphitheatre Pkwy","city":"Mountain View"}]}'
        )

        def json(self):
            return {
                "results": [
                    {
                        "address_line1": "1600 Amphitheatre Pkwy",
                        "city": "Mountain View",
                    }
                ]
            }

    monkeypatch.setattr(system.requests, "get", lambda *_args, **_kwargs: FakeResponse())

    with app.app_context():
        app.config["GEOAPIFY_API_KEY"] = "test-api-key"
        location = system.request_location((37.422, -122.084))

    assert location == "1600 Amphitheatre Pkwy, Mountain View"
