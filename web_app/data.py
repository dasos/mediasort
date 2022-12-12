from codetiming import Timer

import logging

from flask import current_app, g
from flask_executor import Executor
from datetime import datetime

from web_app import system

import MediaFiles
from MediaItem import MediaItem
from MediaSet import MediaSet, MediaSetStore


def clear_db():

  message = "*************************** DELETING FROM DB! ***************************"
  logger = logging.getLogger("mediasort.system.clear_db")
  logger.warning(message)

  redis_client = system.get_db()
  
  #redis_client.flushdb()

  for name in redis_client.scan_iter(match='mediasort:*'):
    redis_client.delete(name)

  ##redis_client.delete("sets")   



def populate_db(force=False):

  logger = logging.getLogger("mediasort.system.populate_db")

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
      redis_client.zadd('mediasort:sets', {set.id: set.start.timestamp() })
      
      # Adds the set into a hash set. This stores a bit of information about the set, which reduces recalculation
      redis_client.hset(f'mediasort:set-meta-{set.id}', mapping = {'length': set.length, 'start': int(set.start.timestamp()), 'end': int(set.end.timestamp()), 'id': set.id})
      
      # Adds the item into a hash set. We'll store some attributes about the item. When we want the media item back, we set them back to what they were it
      # It is perhaps superfluous to add the ID, but we'll pop it in for testing purposes
      redis_client.hset(f'mediasort:item-meta-{item.id}', mapping = {'path': item.path, 'timestamp': item.timestamp.timestamp(), 'id': item.id} )
      
      # Adds the item into a sorted set specific to the set. The timestamp of the item is the score
      # We use this to find the right items to add them back in to the set
      redis_client.zadd(f'mediasort:set-items-{set.id}', {item.id: item.timestamp.timestamp()} )
      
      logger.debug(f'Inserting item id: {item.id} in to set: {set.id}');

    logger.info ("Setting status as done.")
    redis_client.set('mediasort:status', 'done')

#  status = redis_client.get('status')
#  if status == "loading":
#    logger.info ("Status is loading")
#    if force is False:
#      return False
  
  redis_client.set('mediasort:status', 'loading')
  
  if current_app.testing:
    load_data(current_app.config.get('INPUT_DIR'))
  else:
    logger.info ("Starting new thread for load")
    executor = Executor(current_app)
    executor.submit(load_data, current_app.config.get('INPUT_DIR'))
  return


def get_item_path(item_id):
  '''Returns just the path of the item, used in thumbnail creation and in recreating the item'''
  redis_client = system.get_db()
  return redis_client.hget(f'mediasort:item-meta-{item_id}', 'path')


@Timer(name="get_item", text="{name}: {:.4f} seconds")
def get_item(item_id):
  '''Get a single item by its id'''

  logger = logging.getLogger("mediasort.system.get_item")
  
  path = get_item_path(item_id)
  try:
    return MediaItem(path)
  except:
    logger.error (f'File has gone away: {item.orig_filename}')
    raise



@Timer(name="get_set", text="{name}: {:.4f} seconds")
def get_set(set_id, limit = 0, from_end = False, store = False, no_meta = False):
  '''Gets a single set by id, and, by default, all the items in it'''

  logger = logging.getLogger("mediasort.system.get_set")
  
  logger.debug(f"Trying to get set_id: {set_id}")
  
  redis_client = system.get_db()
  
  set = None

  start = 0
  end = limit - 1
  
  if from_end:
    start = 0 - limit
    end = -1
  
  for item_id in redis_client.zrange(f'mediasort:set-items-{set_id}', start, end):

    try:
      item = get_item(item_id)
      
      # By default, it'll regenerate an id. We don't want that
      item.id = item_id
    except Exception:
      logger.warn (f'Skipping item in set')
      continue
  
    if set is None:
      if store is False:
        set = MediaSet(item)
      else:
        set = MediaSetStore(item)
    else:
      set.add_item(item)
  
  # Each time you add an item, you set the length. So we need to do it at the end.
  # This will also set the set id
  # If you don't want to do this (for performance), set no_meta to true
  if no_meta is False: 
    set = set_from_meta(set_id, set)
  return set



def top_tail_set(set_id, limit):
  '''Gets the start and end items of the set, in a "top and tail" style. Ish.'''
  
  # Since we are doing it twice, we will only do half each time
  # TODO: account for odd values of limit
  num_items = int(limit / 2)
  
  # Using no_meta since we'll do it ourselves later
  top = get_set(set_id, num_items, store = True, no_meta = True)
  tail = get_set(set_id, num_items, from_end = True, store = True, no_meta = True)

  # Put everything from tail into top (assuming not already there)
  for x in tail.get_items():
    if not top.check_item_exists(x):
      top.add_item(x)

  # Set the length, start, end, etc, from the meta data stored in Redis
  top = set_from_meta(set_id, top)
  return top


def get_empty_set(set_id, limit = -1, from_end = False, store = False):
  '''Gets a single set by id, with no files, but with the right boundary and length'''
  
  from datetime import datetime
  
  redis_client = system.get_db()
  
  set = set_from_meta(set_id)
  
  return set

def set_from_meta(set_id, s = MediaSet()):
  '''Sets important items about the set from the metadata stored in Redis'''
  
  logger = logging.getLogger("mediasort.system.set_from_meta")
  
  redis_client = system.get_db()
  meta = redis_client.hgetall(f'mediasort:set-meta-{set_id}')
  
  logger.debug (f"Updating set with metadata: {meta}")
  
  s.start = datetime.fromtimestamp(int(meta['start']))
  s.end = datetime.fromtimestamp(int(meta['end']))
  s.length = int(meta['length'])
  s.id = meta['id']
  return s

@Timer(name="get_sets", text="{name}: {:.4f} seconds")
def get_top_tail_sets(num_sets = 5, max_items = 10, reverse = False):
  '''Gets some sets that contain some items in a "top and tail" fashion'''
  redis_client = system.get_db()

  sets = []
  
  for set_id in redis_client.zrange(f'mediasort:sets', start = 0, end = num_sets, desc = reverse):
  
    #sets.append(get_set(set_id, max_items, store=True))
    sets.append(top_tail_set(set_id, max_items))

  return sets













  
