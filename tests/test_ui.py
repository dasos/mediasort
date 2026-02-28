from web_app import create_app


def test_config():
    assert not create_app().testing
    assert create_app({"TESTING": True}).testing


def test_index(client_data):
    response = client_data.get("/")

    assert response.status_code == 200
    assert b"MediaSort" in response.data
    assert b"api/items" in response.data


def test_thumbnail(client_tuple_data):
    client_data, items = client_tuple_data

    id = None
    for x in items:
        if x["path"].endswith(".jpg"):
            id = x["id"]
            break

    assert id is not None

    response = client_data.get(f"/thumbnail/1200/{id}")

    assert response.status_code == 200
    assert response.calculate_content_length() > 1000


def test_thumbnail_missing(client_data):
    response = client_data.get("/thumbnail/99999999")

    assert response.status_code == 404
