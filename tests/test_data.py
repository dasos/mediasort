from web_app import create_app, data, system

import MediaFiles

LIST_OF_MEDIAITEMS = ['images/calculator.jpg', 'images/dup1/leaf.jpg', 'images/dup2/leaf.jpg', 'images/forest.jpg', 'images/grass-video.mp4', 'images/leaf.jpg', 'images/snowy-forest.jpg']
LENGTH_OF_MEDIAITEMS = len(LIST_OF_MEDIAITEMS)
LIST_OF_FILES = sorted(['images/not_this'] + LIST_OF_MEDIAITEMS)
LENGTH_OF_FILES = len(LIST_OF_FILES)

LENGTH_OF_SETS = 4

def test_find_files():
  l = sorted(list(MediaFiles.get_media('images')))

  assert len(l) == LENGTH_OF_FILES
  assert l == LIST_OF_FILES

def test_load_files():
  #for l, s in MediaFiles.load('images'):
  #  print(l, s)
  l, s = zip(*MediaFiles.load('images'))
  assert len(l) == LENGTH_OF_MEDIAITEMS
  
  # Remove duplicates
  unique_s = []
  for i in s:
    if i not in unique_s:
      unique_s.append(i)
      
  assert len(unique_s) == LENGTH_OF_SETS


def test_load_files_redis(app):
  with app.app_context():
    with app.test_request_context():
      data.populate_db()
      
      redis_client = system.get_db()
      
      print (list(redis_client.zrange('mediasort:sets', 0, -1)))
      
      # Get all the sets
      #assert len(list(redis_client.smembers('sets'))) == 3
      assert len(list(redis_client.zrange('mediasort:sets', 0, -1))) == LENGTH_OF_SETS
      
      assert redis_client.zcount('mediasort:sets', '-inf', '+inf') == LENGTH_OF_SETS
      
      # Get all the items
      assert len(list(redis_client.scan_iter(match=f'mediasort:item-meta-*') )) == LENGTH_OF_MEDIAITEMS
      
def test_get_item(redis_client):
  # Get all the items in the DB. Not useful for anything other than testing
  for name in redis_client.scan_iter(match=f'mediasort:item-meta-*'):
    item_id = redis_client.hget(name, 'id')
    path = redis_client.hget(name, 'path')
    item = data.get_item(item_id)
    assert path == item.path

def test_get_sets(redis_client):
  # Get all the sets in the DB.
  for set_id in redis_client.zrange(f'mediasort:sets', 0, -1):
    set = data.get_set(set_id)
    assert set.length >= 1
    
    # Checks the length of the set now against when it was made
    assert set.length == int(redis_client.hget(f'mediasort:set-meta-{set_id}', 'length'))
    
    
def test_get_empty(redis_client):
  # Get all the sets in the DB, but make them empty
  for set_id in redis_client.zrange(f'mediasort:sets', 0, -1):
    set = data.get_empty_set(set_id)
    assert set.length >= 1
    
    
    # Checks the length of the set now against when it was made
    assert set.length == int(redis_client.hget(f'mediasort:set-meta-{set_id}', 'length'))
    assert set.start.timestamp() == int(redis_client.hget(f'mediasort:set-meta-{set_id}', 'start'))
    
def test_get_item_path(redis_client):
  # Get all the items in the DB. Not useful for anything other than testing
  for name in redis_client.scan_iter(match=f'mediasort:item-meta-*'):

    item_id = redis_client.hget(name, 'id')
    
    p1 = redis_client.hget(name, 'path')
    p2 = data.get_item_path(item_id)
    assert p1 == p2
    assert p1 in LIST_OF_FILES