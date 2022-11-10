from web_app import create_app

import MediaFiles
from web_app import data
from web_app.db import get_db

def test_find_files():
  assert list(MediaFiles.get_media('images')) == ['images/forest.jpg', 'images/calculator.jpg', 'images/snowy-forest.jpg', 'images/leaf.jpg', 'images/dup1/leaf.jpg', 'images/dup2/leaf.jpg']

def test_load_files():
  #for l, s in MediaFiles.load('images'):
  #  print(l, s)
  l, s = zip(*MediaFiles.load('images'))
  assert len(l) == 6
  
  # Remove duplicates
  unique_s = []
  for i in s:
    if i not in unique_s:
      unique_s.append(i)
      
  assert len(unique_s) == 3


def test_load_files_redis(app):
  with app.app_context():
    with app.test_request_context():
      data.populate_db()
      
      redis_client = get_db()
      
      print (list(redis_client.zrange('set-start', 0, -1)))
      
      # Get all the sets
      #assert len(list(redis_client.smembers('sets'))) == 3
      assert len(list(redis_client.zrange('set-start', 0, -1))) == 3
      
      assert redis_client.zcount('set-start', '-inf', '+inf') == 3
      
      # Get all the items
      assert len(list(redis_client.scan_iter(match=f'item-*') )) == 6
      
def test_get_item(redis_client):
  # Get all the items in the DB. Not useful for anything other than testing
  for name in redis_client.scan_iter(match=f'item-*'):
    item_id = redis_client.hget(name, 'id')
    path = redis_client.hget(name, 'path')
    item = data.get_item(item_id)
    assert path == item.path

def test_get_sets(redis_client):
  # Get all the sets in the DB.
  for set_id in redis_client.zrange(f'set-start', 0, -1):
    set = data.get_set(set_id)
    assert set.length >= 1
    
    # Checks the length of the set now against when it was made
    assert set.length == int(redis_client.hget(f'set-{set_id}', 'length'))