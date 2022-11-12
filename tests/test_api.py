from web_app import create_app
import json


def test_status(client):
  response = client.get('/api/status')
  
  status = json.loads(response.data)

  assert response.status_code == 200
  assert "status" in status

def test_status_load(client_data):
  response = client_data.get('/api/status')

  status = json.loads(response.data)
  
  assert status["status"] == "done"
  assert status["item_count"] == 7
  
def test_debug(client_data):
  response = client_data.get('/api/debug')

  status = json.loads(response.data)
  
  assert response.status_code == 200
  assert len(status["items"]) == 7
  assert len(status["sets"]) == 4

  #id = (list(status["items"][0].values())[0]['id'])
