import pytest
from web_app import create_app, data


@pytest.fixture
def app(tmp_path):

    db_path = tmp_path / "mediasort.db"

    app = create_app(
        {
            "TESTING": True,
            "INPUT_DIR": "images",
            "DB_PATH": str(db_path),
            "EXECUTOR_PROPAGATE_EXCEPTIONS": True,
        }
    )

    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def client_in_request(app):
    with app.test_request_context():
        yield app.test_client()


@pytest.fixture
def client_data(app):
    with app.app_context():
        data.populate_db()
        yield app.test_client()


@pytest.fixture
def client_tuple_data(app):
    with app.app_context():
        data.populate_db()
        items, _, _ = data.get_items(limit=10000)
        yield app.test_client(), items
