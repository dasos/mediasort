import os
import tempfile

import pytest
from web_app import create_app, data
from web_app.db import get_db


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
def redis_client(app):
  with app.app_context():
    with app.test_request_context():
      data.populate_db()
  
      redis_client = get_db()
  
      yield redis_client