import mediasort
import base64, json
import itertools
import os, pickle, logging
#ImageFile.LOAD_TRUNCATED_IMAGES = True
from io import BytesIO
import requests
from flask import Flask, render_template, request, flash, redirect, url_for, make_response, jsonify
from flask_executor import Executor
from flask_redis import FlaskRedis
from codetiming import Timer

#
# Set up Flask
#

app = Flask(__name__)
if os.environ.get("SECRET_KEY") is not None:
  app.secret_key = os.environ.get("SECRET_KEY")
else:
  app.secret_key = os.urandom(16)

# Get url_for working behind SSL
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)

if os.environ.get("REDIS_URL") is not None:
  app.config['REDIS_URL'] = os.environ.get("REDIS_URL")
else:
  app.config['REDIS_URL'] = "redis://redis:6379/0"

# For most Redis requests
redis_client = FlaskRedis(app, decode_responses=True)
# For when we want the raw data, for when we pickle objects
redis_client_pickled = FlaskRedis(app, decode_responses=False)




app.config['EXECUTOR_PROPAGATE_EXCEPTIONS'] = True 
executor = Executor(app)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(funcName)s - %(message)s'))
logger.addHandler(ch)

def load_config():

  config = {
  	"input_dir": os.environ.get("INPUT") if os.environ.get("INPUT") is not None else "/input",
    "output_dir": os.environ.get("OUTPUT") if os.environ.get("OUTPUT") is not None else "/output",
    "delete_dir": os.environ.get("DELETE") if os.environ.get("DELETE") is not None else "/delete",
    "thumbnails": os.environ.get("THUMBNAILS") if os.environ.get("THUMBNAILS") is not None else 6,
  }
  logger.info(f'Using {config["input_dir"]} as the input directory')
    
  return config


def initial_load():
  status = redis_client.get('status')
  if status == "loading":
    logger.warning("Unclean shutdown. Resetting flag")
    redis_client.set('status', '')


config = load_config()
initial_load()



def populate_db(force=False):

  def load_data(input_dir):
    # Get all the sets as a list
    def save_item(item, set):
      redis_client.hset(f'set-meta-{set.id}', 'start', set.start.timestamp())
      redis_client.sadd('sets', set.id)
      redis_client.sadd(f'set-list-{set.id}', item.id)
      redis_client.set(f'item-{set.id}-{item.id}', pickle.dumps(item))
      logger.debug(f'Inserting item id: {item.id} in to set: {set.id}');
      
    mediasort.load(config["input_dir"], save_item)
    logging.info ("Setting status as done.")
    redis_client.set('status', 'done')

  status = redis_client.get('status')
  if status == "loading":
    logger.info ("Status is loading")
    if force is False:
      return False
  
  logger.info ("Starting new thread for load")
  redis_client.set('status', 'loading')
  executor.submit(load_data, config["input_dir"])
  return

#
# Looks in Redis for items with a matching set_id. Then dynamically makes a new set, and puts the unpickled items in it
#
@Timer(name="get_set", text="{name}: {:.4f} seconds")
def get_set(set_id, start=0, limit=None): # By default unlimited
  
  set = None

  # Notice the limit here
  for item_id in sorted(redis_client.smembers(f'set-list-{set_id}'))[start:limit]:
#  for name in redis_client.scan_iter(match=f'item-{set_id}-*', count=100):
    logger.debug (f'Dealing with item-{set_id}-{item_id}')
    try:
      item = pickle.loads(redis_client_pickled.get(f'item-{set_id}-{item_id}'))
    except FileNotFoundError:
      logger.error (f'File has gone away: {item.orig_filename}')
      redis_client.delete(f'item-{set_id}-{item_id}')
      continue
    
    logger.info (f'Item: {item}')
    if set is None:
      logger.debug ('Dynamically creating new set')
      set = mediasort.MediaSet(item)
      set.id = set_id
      length = len(sorted(redis_client.smembers(f'set-list-{set_id}')))
      set.length = length
      logger.debug (f'Set length to {set.length}')
    else:
      logger.debug ('Adding to existing set')
      set.add_item(item)
      # Need to reset the length to the full set
      set.length = length
  
  if not set:
    logger.error (f'Missing set. set_id: {set_id}')
    raise TypeError
  
  
  # Resetting the start time, in case it has changed
  redis_client.hset(f'set-meta-{set_id}', 'start', set.start.timestamp())
  

  
  return set

#
# Unpickles a MediaItem from Redis
#
@Timer(name="get_item", text="{name}: {:.4f} seconds")
def get_item(set_id, item_id): # TO DO, remove the need for set_id
  return pickle.loads(redis_client_pickled.get(f'item-{set_id}-{item_id}'))

@Timer(name="get_sets", text="{name}: {:.4f} seconds")
def get_sets(limit = 5, num_thumbnails = 10):
  sets = []
  for s in redis_client.sort('sets', by='set-meta-*->start', num=limit, start=0):
    #try:
      sets.append(get_set(s, limit=num_thumbnails))
    #except TypeError:
    #  logger.error (f"Couldn't find set, so cleaning up {s}")
    #  redis_client.delete('set-meta-{s}')
    #  redis_client.delete('set-list-{s}')
    #  redis_client.srem('sets', s)
  
  return sets

#
# Generates the basic HTML page
#
  

@app.route('/')
def index():

  num_thumbnails = config.get('thumbnails')

  sets = get_sets(5, num_thumbnails)


  return render_template('index.html', sets=sets, num_thumbnails=num_thumbnails, base_path=config.get("input_dir"))

@Timer(name="reload", text="{name}: {:.4f} seconds")
@app.route('/reload')
def reload_data():
  
  status = redis_client.get('status')
  if status == "loading":
    logger.warning ("Already loading. To force, restart the app");
    flash("Already loading", 'warning')
    return redirect(url_for('index'))
    
  print ("*************************** FLUSHING ITEMS! ***************************")
  
  
  for name in redis_client.scan_iter(match='item-*'):
    redis_client.delete(name)

  # This deletes set-list-* and set-meta-*
  for name in redis_client.scan_iter(match='set-*'):
    redis_client.delete(name)  

  redis_client.delete("sets")    
  
  
  #redis_client.flushdb()
  populate_db()
  flash("Refreshing sets from files")
  return redirect(url_for('index'))
  

@app.route('/status')
def get_result():

  data = {
    'item_count': len(list(redis_client.scan_iter(match='item-*'))),
    'set_count': len(list(redis_client.scan_iter(match='set-meta-*'))),
    'status': redis_client.get('status')
  }

  return jsonify(data)
  
#
# Generates the thumbnails
#

@app.route('/thumbnail/<int:set_id>/<int:photo_id>.jpg')
@app.route('/thumbnail/<int:size>/<int:set_id>/<int:photo_id>.jpg')
def get_thumbnail(set_id, photo_id, size=300):
  item = get_item(set_id, photo_id)
  
  #item = set.set[photo_id]
  thumbnail = make_thumbnail(item.path, size)

  response = make_response(thumbnail)
  response.content_type = 'image/jpeg'
  return response

@app.route('/location/<int:set_id>/<int:photo_id>')
def get_location(set_id, photo_id):
  item = get_item(set_id, photo_id)
  
  if not item.coords:
    return ""
  
  rounded_coords = round(float(item.coords[0]), 4), round(float(item.coords[1]), 4)
  rounded_coords_key = f'coord-{rounded_coords[0]}-{rounded_coords[1]}'
  
  if redis_client.exists(rounded_coords_key):
    return redis_client.get(rounded_coords_key)
  
  result = request_location(rounded_coords)
  
  redis_client.set(rounded_coords_key, result)
  
  return result
  
def request_location(coords):
  payload = {'lat': coords[0], 'lon': coords[1]}

  r = requests.get('https://photon.komoot.io/reverse', params=payload)
  
  if "features" not in r.json() or len(r.json()["features"]) != 1:
    logger.warning (f'Could not find location feature in : {r.text}')
    return ""
    
  result = r.json()["features"][0]["properties"]
  
  if "name" in result:
    return result["name"]
  
  if "city" in result:
    return result["city"]
    
  return result
    
#
# Removes an item from a set.
#

@app.route('/remove/<int:set_id>/<int:photo_id>', methods=('POST',))
def delete_from_set(set_id, photo_id):
  
  set = get_set(set_id)
  item = None
  
  # Finding the item in the set "manually", rather than recreating it again from Redis
  for i in set.set:
    if i.id == photo_id:
      item = i
      set.remove_item(i)
      break
  
  if item is None:
    raise Exception("Could not find item in old set")
  
  
  new_set = mediasort.MediaSet(item)
  
  # Update existing set, in case start time has changed
  redis_client.hset(f'set-meta-{set.id}', 'start', set.start.timestamp())
  
  # Remove item
  redis_client.srem(f'set-list-{set_id}', item.id)
  redis_client.delete(f'item-{set_id}-{item.id}')
  logger.info(f"Removing item from Redis: item-{set.id}-{item.id}")
  
  # Add new set
  redis_client.sadd('sets', new_set.id)
  redis_client.sadd(f'set-list-{new_set.id}', item.id)
  redis_client.hset(f'set-meta-{new_set.id}', 'start', new_set.start.timestamp())
  redis_client.set(f'item-{new_set.id}-{item.id}', pickle.dumps(item))
  logger.info(f"Adding item to Redis: item-{new_set.id}-{item.id}")
  
  
  flash(f'Removed {item.dest_filename}')
  return redirect(url_for('index'))

#
# Gets more thumbnails for a set
#
@app.route('/set/<int:set_id>')
def more_thumbnails(set_id):

  start = request.args.get('start', default = 0, type = int)
  end = request.args.get('end', default = 6, type = int)

  
  set = get_set(set_id, start, end)
  if not set:
    return 'Could not find set.', 400
  
  return render_template('thumbnails.html', set=set, start=start, end=end, base_path=config.get("input_dir"))


#
# Actions a set, by moving all the items in it.
#

#@app.route('/', methods=('POST',))
@app.route('/set/<int:set_id>', methods=('POST',))
def post(set_id):

  # The function that is executed in a thread
  def actually_move(set, name):
    # With date
    if request.form.get("action") == "save_date" or request.form.get("action") == "save_no_date":
        
      set.set_name(name)
      if request.form.get("action") == "save_date":
        dir = mediasort.move_all_in_set(set, config['output_dir']) 
      else:
        dir = mediasort.move_all_in_set(set, config['output_dir'], use_date_directory=False)
      
      print(f'Files saved in {dir}')
      
    # Delete
    elif request.form.get("action") == "delete":
      dir = mediasort.move_all_in_set(set, config['delete_dir'], use_date_directory=False, use_name_directory=False)
      
      print(f'Files saved in {dir}')
      
    else:
      print("Doing nothing, no command")

  try:
    set = get_set(set_id)
  except:
    flash('Could not find set', 'warning')
    return redirect(url_for('index'))
    
  if request.form.get("action") == "save_date" or request.form.get("action") == "save_no_date":
    if request.form.get('name'):
      # Adding the name as a suggestion
      redis_client.sadd('suggestions', request.form.get('name'))
    else:
      flash('You must provide a name to save', 'warning')
      return redirect(url_for('index'))

  # Perhaps optimistically, remove the information *before* it is actioned. We don't want have it interacted with again. If it goes wrong, it can be rescanned
  logger.info ("Removing set information from Redis")
  redis_client.delete(f'set-meta-{set.id}')
  redis_client.delete(f'set-list-{set.id}')
  redis_client.srem('sets', set.id)
  for name in redis_client.scan_iter(match=f'item-{set.id}-*'):
    redis_client.delete(name)
    
    

  print ("Starting new thread for set move")
  flash("Moving set in background")
  executor.submit(actually_move, set, str(request.form.get('name')))
    
  return redirect(url_for('index'))

@app.route('/suggestions.json')
def names():
  return json.dumps(list(redis_client.smembers('suggestions')))
#  return json.dumps(['Arthur', 'Henry', 'Cats']);

def make_thumbnail(filename, wh=300):
  from PIL import UnidentifiedImageError
  try:
    return make_thumbnail_pil(filename, wh)
  except UnidentifiedImageError:
    logger.info("Could not generate thumbnail")
    return ""

def make_thumbnail_pil(filename, wh):
  from PIL import Image
  size = (wh,wh)
  buffered = BytesIO()
  im = Image.open(filename)
  im.thumbnail(size)
  im.save(buffered, format="JPEG")
  return buffered.getvalue()
  
#def make_thumbnail_cv2(filename, wh):
#  import cv2
#  video = cv2.VideoCapture(filename)
#  status, image = video.read()
#
#  width = wh
#  height = int(width * image.shape[0] / image.shape[1])
#  im = cv2.resize(image, (width, height), interpolation = cv2.INTER_AREA)
#  is_success, im_buf_arr = cv2.imencode(".jpg", im)
#  return im_buf_arr.tobytes() 

