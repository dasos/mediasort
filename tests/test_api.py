from web_app import create_app, system
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
    assert len(status["sets"]) == test_data.LENGTH_OF_SETS

    # id = (list(status["items"][0].values())[0]['id'])


def test_suggestions(client_data):
    response = client_data.get("/api/suggestions")

    status = json.loads(response.data)

    assert response.status_code == 200
    assert status == []


def test_suggestions_content(client_data):
    redis_client = system.get_db()
    redis_client.sadd("mediasort:suggestions", "test")

    response = client_data.get("/api/suggestions")

    status = json.loads(response.data)

    assert response.status_code == 200
    assert status == ["test"]


def test_move_set(client_tuple_data):

    client, _, sets = client_tuple_data

    response = client.get("/api/debug")
    print(json.loads(response.data))

    set_id = sets[0]["id"]

    formdata = {"name": "hello_world"}
    response = client.post(f"/api/set/save_date/{set_id}", data=formdata)

    print(response)

    assert response.status_code == 200
    assert json.loads(response.data)["data"]["result"] == "OK"

    set_id = sets[1]["id"]

    formdata = {"name": "hello_world"}
    response = client.post(f"/api/set/save_no_date/{set_id}", data=formdata)

    assert json.loads(response.data)["data"]["result"] == "OK"

    set_id = sets[2]["id"]

    formdata = {"name": "hello_world"}
    response = client.post(f"/api/set/delete/{set_id}", data=formdata)

    assert json.loads(response.data)["data"]["result"] == "OK"

    response = client.get("/api/debug")

    print(response)

    assert len(json.loads(response.data)["sets"]) == test_data.LENGTH_OF_SETS - 3
