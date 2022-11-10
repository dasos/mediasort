from web_app import create_app

import MediaFiles
from web_app import data, system

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
      
      redis_client = system.get_db()
      
      print (list(redis_client.zrange('sets', 0, -1)))
      
      # Get all the sets
      #assert len(list(redis_client.smembers('sets'))) == 3
      assert len(list(redis_client.zrange('sets', 0, -1))) == 3
      
      assert redis_client.zcount('sets', '-inf', '+inf') == 3
      
      # Get all the items
      assert len(list(redis_client.scan_iter(match=f'item-meta-*') )) == 6
      
def test_get_item(redis_client):
  # Get all the items in the DB. Not useful for anything other than testing
  for name in redis_client.scan_iter(match=f'item-meta-*'):
    item_id = redis_client.hget(name, 'id')
    path = redis_client.hget(name, 'path')
    item = data.get_item(item_id)
    assert path == item.path

def test_get_sets(redis_client):
  # Get all the sets in the DB.
  for set_id in redis_client.zrange(f'sets', 0, -1):
    set = data.get_set(set_id)
    assert set.length >= 1
    
    # Checks the length of the set now against when it was made
    assert set.length == int(redis_client.hget(f'set-meta-{set_id}', 'length'))
    
    
def test_get_empty(redis_client):
  # Get all the sets in the DB, but make them empty
  for set_id in redis_client.zrange(f'sets', 0, -1):
    set = data.get_empty_set(set_id)
    assert set.length >= 1
    
    
    # Checks the length of the set now against when it was made
    assert set.length == int(redis_client.hget(f'set-meta-{set_id}', 'length'))
    assert set.start.timestamp() == int(redis_client.hget(f'set-meta-{set_id}', 'start'))
    
def test_get_item_path(redis_client):
  # Get all the items in the DB. Not useful for anything other than testing
  for name in redis_client.scan_iter(match=f'item-meta-*'):

    item_id = redis_client.hget(name, 'id')
    
    p1 = redis_client.hget(name, 'path')
    p2 = data.get_item_path(item_id)
    assert p1 == p2
    assert p1 in ['images/forest.jpg', 'images/leaf.jpg', 'images/calculator.jpg',  'images/snowy-forest.jpg', 'images/dup1/leaf.jpg', 'images/dup2/leaf.jpg']