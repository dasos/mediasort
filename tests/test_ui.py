from web_app import create_app


def test_config():
    assert not create_app().testing
    assert create_app({"TESTING": True}).testing


def test_index(client_data):
    response = client_data.get("/")

    assert b"forest.jpg" in response.data
    assert b"save" in response.data
    assert b"2022-01-01" in response.data

def test_more_sets(client_data):
    response = client_data.get("/set/more_from/2")

    assert b"leaf.jpg" in response.data

def test_thumbnail(client_tuple_data):

    # Unpack the tuple
    client_data, items, _ = client_tuple_data

    for x in items:
        if "jpg" in x["path"]:
            id = x["id"]
            break

    response = client_data.get(f"/thumbnail/1200/{id}.jpg")

    assert response.status_code == 200
    assert response.calculate_content_length() > 1000


def test_get_set(client_tuple_data):

    # Unpack the tuple
    client_data, _, sets = client_tuple_data

    print(sets)

    response = client_data.get(f'/set/{sets[0]["id"]}')

    assert response.status_code == 200
    assert b"save" in response.data
