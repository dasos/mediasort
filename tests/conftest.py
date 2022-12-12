import os
import tempfile

import pytest
from web_app import create_app, data, system


@pytest.fixture
def app():

    app = create_app({
        'TESTING': True,
        'INPUT_DIR': 'images',
        'EXECUTOR_PROPAGATE_EXCEPTIONS': True,
    })
    
    return app


@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def client_in_request(app):
  with app.test_request_context():
    yield app.test_client()

@pytest.fixture
def redis_client(app):
  with app.app_context():
    with app.test_request_context():
      data.populate_db()
  
      redis_client = system.get_db()
  
      yield redis_client
      

@pytest.fixture
def client_data(app):
  with app.app_context():
    
    data.populate_db()

    yield app.test_client()

@pytest.fixture
def client_tuple_data(app):
  with app.app_context():
    
    data.populate_db()
    
    redis_client = system.get_db()
    
    items = [redis_client.hgetall(name) for name in redis_client.scan_iter(match='mediasort:item-meta-*')]
    sets = [redis_client.hgetall(name) for name in redis_client.scan_iter(match='mediasort:set-meta-*')]
    
    yield app.test_client(), items, sets