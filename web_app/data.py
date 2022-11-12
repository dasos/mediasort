from codetiming import Timer

from flask import current_app, g
from flask_executor import Executor

from web_app import system

import MediaFiles
from MediaItem import MediaItem
from MediaSet import MediaSet, MediaSetStore


def clear_db():

  message = "*************************** DELETING FROM DB! ***************************"
  current_app.logger.warn(message)
  print (message)

  redis_client = system.get_db()
  
  redis_client.flushdb()

  for name in redis_client.scan_iter(match='item-*'):
    redis_client.delete(name)

  # This deletes set-list-* and set-meta-*
  for name in redis_client.scan_iter(match='set-*'):
    redis_client.delete(name)  

  ##redis_client.delete("sets")   



def populate_db(force=False):

  redis_client = system.get_db()

  def load_data(input_dir):
    
    for item, set in MediaFiles.load(input_dir):
    
      # This stores the timestamps and other information about a set. It is used for sorting
      # redis_client.hset(f'set-meta-{set.id}', mapping = {'start': int(set.start.timestamp()), 'end': int(set.end.timestamp())})
      # This stores the set id. We sort this using the attributes added above
      #redis_client.sadd('sets', set.id)
      # This stores the item. We are just storing the filename. When we want the media item back, we recreate it
      #redis_client.sadd(f'set-items-{set.id}', item.path)
      
      # Adds the set into a sorted set, which has the start time as the score
      redis_client.zadd('sets', {set.id: set.start.timestamp() })
      
      # Adds the set into a hash set. This stores a bit of information about the set, which reduces recalculation
      redis_client.hset(f'set-meta-{set.id}', mapping = {'length': set.length, 'start': int(set.start.timestamp()), 'end': int(set.end.timestamp()), 'id': set.id})
      
      # Adds the item into a hash set. We'll store some attributes about the item. When we want the media item back, we set them back to what they were it
      # It is perhaps superfluous to add the ID, but we'll pop it in for testing purposes
      redis_client.hset(f'item-meta-{item.id}', mapping = {'path': item.path, 'timestamp': item.timestamp.timestamp(), 'id': item.id} )
      
      # Adds the item into a sorted set specific to the set. The timestamp of the item is the score
      # We use this to find the right items to add them back in to the set
      redis_client.zadd(f'set-items-{set.id}', {item.id: item.timestamp.timestamp()} )
      
      current_app.logger.debug(f'Inserting item id: {item.id} in to set: {set.id}');

    current_app.logger.info ("Setting status as done.")
    redis_client.set('status', 'done')

#  status = redis_client.get('status')
#  if status == "loading":
#    logger.info ("Status is loading")
#    if force is False:
#      return False
  
  print ("LOADING")
  redis_client.set('status', 'loading')
  
  if current_app.testing:
    load_data(current_app.config.get('INPUT_DIR'))
  else:
    current_app.logger.info ("Starting new thread for load")
    executor = Executor(current_app)
    executor.submit(load_data, current_app.config.get('INPUT_DIR'))
  return


def get_item_path(item_id):
  '''Returns just the path of the item, used in thumbnail creation and in recreating the item'''
  redis_client = system.get_db()
  return redis_client.hget(f'item-meta-{item_id}', 'path')


@Timer(name="get_item", text="{name}: {:.4f} seconds")
def get_item(item_id):
  '''Get a single item by its id'''
  path = get_item_path(item_id)
  try:
    return MediaItem(path)
  except:
    current_app.logger.error (f'File has gone away: {item.orig_filename}')
    raise



@Timer(name="get_set", text="{name}: {:.4f} seconds")
def get_set(set_id, limit = -1, from_end = False, store = False):
  '''Gets a single set by id, and, by default, all the items in it'''
  redis_client = system.get_db()
  
  set = None

  start = 0
  end = limit
  
  if from_end:
    start = 0 - limit
    end = -1
  
  
  for item_id in redis_client.zrange(f'set-items-{set_id}', start, end):

    try:
      item = get_item(item_id)
      
      # By default, it'll regenerate an id. We don't want that
      item.id = item_id
    except Exception:
      current_app.logger.warn (f'Skipping item in set')
      continue
  
    if set is None:
      if store is False:
        set = MediaSet(item)
      else:
        set = MediaSetStore(item)
    else:
      set.add_item(item)
  
  return set

def get_empty_set(set_id, limit = -1, from_end = False, store = False):
  '''Gets a single set by id, with no files, but with the right boundary and length'''
  
  from datetime import datetime
  
  redis_client = system.get_db()
  
  set = MediaSet()
  
  meta = redis_client.hgetall(f'set-meta-{set_id}')
  set.start = datetime.fromtimestamp(int(meta['start']))
  set.end = datetime.fromtimestamp(int(meta['end']))
  set.length = int(meta['length'])
  
  return set

@Timer(name="get_sets", text="{name}: {:.4f} seconds")
def get_sets(limit = 5, max_items = 10, reverse = False):
  redis_client = system.get_db()

  sets = []
  
  for set_id in redis_client.zrange(f'sets', start = 0, end = limit, desc = reverse):

    sets.append(get_set(set_id, max_items, store=True))

  return sets













  
