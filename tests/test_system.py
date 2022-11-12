from web_app import system

def test_thumbnail():
  thumbnail = system.make_thumbnail('images/leaf.jpg')
  
  assert len(thumbnail) > 7000 and len(thumbnail) < 10000

def test_location(redis_client):

  location = system.get_location((51.50084130000768, -0.14298782563424842))
  
  assert location == "Buckingham Palace"