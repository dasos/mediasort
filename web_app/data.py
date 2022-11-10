from codetiming import Timer

from flask import current_app, g
from flask_executor import Executor

from web_app.db import get_db

import MediaFiles
from MediaItem import MediaItem
from MediaSet import MediaSet


def populate_db(force=False):

  redis_client = get_db()

  def load_data(input_dir):
    
    for item, set in MediaFiles.load(input_dir):
    
      # This stores the timestamps and other information about a set. It is used for sorting
      # redis_client.hset(f'set-meta-{set.id}', mapping = {'start': int(set.start.timestamp()), 'end': int(set.end.timestamp())})
      # This stores the set id. We sort this using the attributes added above
      #redis_client.sadd('sets', set.id)
      # This stores the item. We are just storing the filename. When we want the media item back, we recreate it
      #redis_client.sadd(f'set-items-{set.id}', item.path)
      
      # Adds the set into a sorted set, which has the start time as the score
      redis_client.zadd('set-start', {set.id: set.start.timestamp() })
      
      # Adds the set into a has set. This stores a bit of information about the set, which reduces recalculation
      redis_client.hset(f'set-{set.id}', mapping = {'length': set.length, 'start': int(set.start.timestamp()), 'end': int(set.end.timestamp())  })
      
      # Adds the item into a hash set. We'll store some attributes about the item. When we want the media item back, we recreate it
      # It is superfluous to add the ID, but we'll pop it in for testing purposes
      redis_client.hset(f'item-{item.id}', mapping = {'path': item.path, 'timestamp': item.timestamp.timestamp(), 'id': item.id} )
      
      # Adds the item into a sorted set specific to the set. The timestamp of the item is the score
      redis_client.zadd(f'set-{set.id}-time', {item.id: item.timestamp.timestamp()} )
      
      current_app.logger.debug(f'Inserting item id: {item.id} in to set: {set.id}');

    current_app.logger.info ("Setting status as done.")
    redis_client.set('status', 'done')

#  status = redis_client.get('status')
#  if status == "loading":
#    logger.info ("Status is loading")
#    if force is False:
#      return False
  
  current_app.logger.info ("Starting new thread for load")
  redis_client.set('status', 'loading')
  
  if current_app.testing:
    load_data(current_app.config.get('INPUT_DIR'))
  else:
    executor = Executor(current_app)
    executor.submit(load_data, current_app.config.get('INPUT_DIR'))
  return





@Timer(name="get_item", text="{name}: {:.4f} seconds")
def get_item(item_id):
  '''Get a single item by its id'''
  redis_client = get_db()
  path = redis_client.hget(f'item-{item_id}', 'path')
  try:
    return MediaItem(path)
  except:
    current_app.logger.error (f'File has gone away: {item.orig_filename}')
    raise



@Timer(name="get_set", text="{name}: {:.4f} seconds")
def get_set(set_id, limit = -1, from_end = False):
  '''Gets a single set by id, and, by default, all the items in it'''
  redis_client = get_db()
  
  set = None

  start = 0
  end = limit
  
  if from_end:
    start = 0 - limit
    end = -1
  
  
  for item_id in redis_client.zrange(f'set-{set_id}-time', start, end):

    try:
      item = get_item(item_id)
    except Exception:
      current_app.logger.warn (f'Skipping item in set')
      continue
  
    if set is None:
      set = MediaSet(item)
    else:
      set.add_item(item)
  
  return set


@Timer(name="get_sets", text="{name}: {:.4f} seconds")
def get_sets(limit = 5, max_items = 10, reverse = False):
  redis_client = get_db()

  sets = []
  
  for set_id in redis_client.zrange(f'set-start', start = 0, end = limit, desc = reverse):
    set = get_set(set_id)
    sets.append(get_set(set_id, max_items))

  return sets













  
