from web_app import create_app


def test_status(client):
  response = client.get('/api/status')
  print(response)
  assert b"status" in response.data