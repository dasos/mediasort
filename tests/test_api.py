from web_app import data
import json

import test_data


def test_status(client):
    response = client.get("/api/status")

    status = json.loads(response.data)

    assert response.status_code == 200
    assert "status" in status


def test_status_load(client_data):
    response = client_data.get("/api/status")

    status = json.loads(response.data)

    assert status["status"] == "done"
    assert status["item_count"] == test_data.LENGTH_OF_MEDIAITEMS


def test_reload(client_in_request):
    response = client_in_request.get("/api/status")
    status = json.loads(response.data)
    assert status["item_count"] == 0

    response = client_in_request.get("/api/reload")
    status = json.loads(response.data)
    assert response.status_code == 200

    response = client_in_request.get("/api/status")
    status = json.loads(response.data)
    assert status["item_count"] == test_data.LENGTH_OF_MEDIAITEMS


def test_debug(client_data):
    response = client_data.get("/api/debug")

    status = json.loads(response.data)

    assert response.status_code == 200
    assert len(status["items"]) == test_data.LENGTH_OF_MEDIAITEMS


def test_suggestions(client_data):
    response = client_data.get("/api/suggestions")

    status = json.loads(response.data)

    assert response.status_code == 200
    assert status == []


def test_suggestions_content(client_data, app):
    with app.app_context():
        data.add_suggestion("test")

    response = client_data.get("/api/suggestions")

    status = json.loads(response.data)

    assert response.status_code == 200
    assert status == ["test"]


def test_items_api(client_data):
    response = client_data.get("/api/items?limit=3")

    status = json.loads(response.data)

    assert response.status_code == 200
    assert len(status["items"]) == 3
    assert status["next_after"] is not None


def test_items_api_pagination(client_data):
    first = client_data.get("/api/items?limit=3")
    first_payload = json.loads(first.data)

    after = first_payload["next_after"]
    response = client_data.get(
        f"/api/items?limit=3&after_ts={after['timestamp']}&after_id={after['id']}"
    )
    payload = json.loads(response.data)

    assert response.status_code == 200
    assert len(payload["items"]) == 3
    assert payload["items"][0]["id"] != first_payload["items"][-1]["id"]


def test_move_set(client_tuple_data, app):

    client, items = client_tuple_data

    item_ids = [item["id"] for item in items]

    set_one = item_ids[:2]
    set_two = item_ids[2:4]
    set_three = item_ids[4:5]

    formdata = {"name": "hello_world", "item_ids": set_one}
    response = client.post("/api/set/save_date", json=formdata)

    assert response.status_code == 200
    assert json.loads(response.data)["data"]["result"] == "OK"

    formdata = {"name": "hello_world", "item_ids": set_two}
    response = client.post("/api/set/save_no_date", json=formdata)

    assert json.loads(response.data)["data"]["result"] == "OK"

    formdata = {"name": "hello_world", "item_ids": set_three}
    response = client.post("/api/set/delete", json=formdata)

    assert json.loads(response.data)["data"]["result"] == "OK"

    with app.app_context():
        remaining = data.get_item_count()

    assert remaining == test_data.LENGTH_OF_MEDIAITEMS - (
        len(set_one) + len(set_two) + len(set_three)
    )


def test_move_set_invalid_item_ids(client_data):
    response = client_data.post("/api/set/save_date", json={"item_ids": ["nope"]})

    assert response.status_code == 400
