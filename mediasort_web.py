import mediasort
import base64, json
import itertools
import os, pickle
#ImageFile.LOAD_TRUNCATED_IMAGES = True
from io import BytesIO
import requests
from flask import Flask, render_template, request, flash, redirect, url_for, make_response, session, jsonify
from flask_executor import Executor
from flask_redis import FlaskRedis

#
# Set up Flask
#

app = Flask(__name__)
if os.environ.get("SECRET_KEY") is not None:
  app.secret_key = os.environ.get("SECRET_KEY")
else:
  app.secret_key = os.urandom(16)

#app.config['SESSION_TYPE'] = 'filesystem'
#Session(app)  

if os.environ.get("REDIS_URL") is not None:
  app.config['REDIS_URL'] = os.environ.get("REDIS_URL")
else:
  app.config['REDIS_URL'] = "redis://redis:6379/0"

redis_client = FlaskRedis(app, decode_responses=True)
redis_client_pickled = FlaskRedis(app, decode_responses=False)




app.config['EXECUTOR_PROPAGATE_EXCEPTIONS'] = True 
executor = Executor(app)

def load_config():

  config = { "input_dir": "/input", "output_dir": "/output", "delete_dir": "/delete", "thumbnails": 6, "suggestions": ["arthur", "henry"] }
  try:
    with open("config.json") as json_file:
      loaded = json.load(json_file)
      config.update(loaded)
  except Exception:
    print ("Could not load config.json file. Defaults will be used")
    
  print(config["input_dir"])
    
  return config

config = load_config()


def populate_db():

  def load_data(input_dir):
    # Get all the sets as a list
    def save_item(item, set):
      redis_client.hset('set-{}'.format(set.id), 'start', set.start.timestamp())
      redis_client.sadd('sets', set.id)
      redis_client.set('item-{}-{}'.format(set.id, item.id), pickle.dumps(item))
      #print ('INSERTING: item-{}-{}'.format(item.set.id, item.id))
      
    mediasort.load(config["input_dir"], save_item)

  
  executor.submit_stored('load', load_data, config["input_dir"])
  session['loaded'] = True
  return

  
#
# Looks in Redis for items with a matching set_id. Then dynamically makes a new set, and puts the unpickled items in it
#

def get_set(set_id):
  
  set = None

  for name in redis_client.scan_iter(match='item-{}-*'.format(set_id)):

    try:
      item = pickle.loads(redis_client_pickled.get(name))
    except FileNotFoundError:
      print ("File has gone away")
      redis_client.delete(name)
      continue
      
    if set is None:
      set = mediasort.MediaSet(item)
      set.id = set_id
    else:
      set.add_item(item)
  
  if not set:
    raise Exception("Missing set. set_id: {}".format(set_id))
  
  # Resetting the start time, in case it has changed
  redis_client.hset('set-{}'.format(set_id), 'start', set.start.timestamp())
  
  return set

#
# Unpickles a MediaItem from Redis
#

def get_item(set_id, item_id):
  return pickle.loads(redis_client_pickled.get('item-{}-{}'.format(set_id, item_id)))


def get_sets(limit = 5):
  return [get_set(s) for s in redis_client.sort('sets', by='set-*->start', num=limit, start=0)]

#
# Generates the basic HTML page
#

@app.route('/')
def index():
  sets = get_sets()
  if not sets and not 'loaded' in session and not executor.futures.running('load'):
    print ("Could not find any sets in Redis. Attempting to refresh")
    populate_db()

  return render_template('index.html', sets=sets, num_thumbnails=config.get('thumbnails'), base_path=config.get("input_dir"))


@app.route('/reload')
def reload_data():
  if executor.futures.running('load'):
    flash("Already loading", 'warning')
    return redirect(url_for('index'))
    
  print ("*************************** FLUSHING DB! ***************************")
  redis_client.flushdb()
  populate_db()
  flash("Refreshing sets from files")
  return redirect(url_for('index'))
  

@app.route('/status')
def get_result():

  data = {
  	'item_count': len(list(redis_client.scan_iter(match='item-*'))),
  	'set_count': len(list(redis_client.scan_iter(match='set-*')))
  }

  if executor.futures.running('load'):
    data['status'] = 'in_progress'
    return jsonify(data)

  if executor.futures.done('load'):
    print ("Load complete")
    executor.futures.pop('load')

  data['status'] = 'done'
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
  
  if item.coords is None:
    return ""
  
  rounded_coords = round(float(item.coords[0]), 5), round(float(item.coords[1]), 5)
  rounded_coords_key = 'coord-{}-{}'.format(rounded_coords[0], rounded_coords[1])
  
  if redis_client.exists(rounded_coords_key):
    return redis_client.get(rounded_coords_key)
  
  result = request_location(rounded_coords)
  
  redis_client.set(rounded_coords_key, result)
  
  return result
  
def request_location(coords):
  payload = {'lat': coords[0], 'lon': coords[1]}

  r = requests.get('https://photon.komoot.io/reverse', params=payload)
  
  if "features" not in r.json() or len(r.json()["features"]) != 1:
    print (r.text)
    return ""
    
  result = r.json()["features"][0]["properties"]
  
  print (result)
  
  if "city" in result:
    return result["city"]
    
  if "name" in result:
    return result["name"]
    
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
  redis_client.hset('set-{}'.format(set.id), 'start', set.start.timestamp())
  
  # Remove item
  redis_client.delete('item-{}-{}'.format(set.id, item.id))
  print("Removing item from Redis: item-{}-{}".format(set.id, item.id))
  
  # Add new set
  redis_client.hset('set-{}'.format(new_set.id), 'start', new_set.start.timestamp())
  redis_client.sadd('sets', new_set.id)
  redis_client.set('item-{}-{}'.format(new_set.id, item.id), pickle.dumps(item))
  print("Adding item to Redis: item-{}-{}".format(new_set.id, item.id))
  
  
  flash('Removed {}'.format(item.dest_filename))
  return redirect(url_for('index'))

#
# Gets more thumbnails for a set
#
@app.route('/set/<int:set_id>')
def more_thumbnails(set_id):
  set = get_set(set_id)
  if not set:
    return 'Could not find set.', 400
  start = request.args.get('start', default = 0, type = int)
  end = request.args.get('end', default = 6, type = int)
  
  return render_template('thumbnails.html', set=set, start=start, end=end, base_path=config.get("input_dir"))

#
# Actions a set, by moving all the items in it.
#

#@app.route('/', methods=('POST',))
@app.route('/set/<int:set_id>', methods=('POST',))
def post(set_id):


  def del_redis_set(set):
    #redis_client.hdel('set-{}'.format(set.id), 'start')
    redis_client.delete('set-{}'.format(set.id))
    redis_client.srem('sets', set.id)
    for name in redis_client.scan_iter(match='item-{}-*'.format(set.id)):
      redis_client.delete(name)
    


  set = get_set(set_id)
  if (not set):
    flash('Could not find set', 'warning')
    return redirect(url_for('index'))
  
  # With date
  if request.form.get("action") == "save_date" or request.form.get("action") == "save_no_date":
    if not request.form.get('name'):
      flash('You must provide a name to save', 'warning')
      return redirect(url_for('index'))
      
    set.set_name(str(request.form.get('name')))
    if request.form.get("action") == "save_date":
      dir = mediasort.move_all_in_set(set, config['output_dir']) 
    else:
      dir = mediasort.move_all_in_set(set, config['output_dir'], use_date_directory=False)
    
    del_redis_set(set)
    flash('Saved in {}'.format(dir))
    
  # Delete
  elif request.form.get("action") == "delete":
    dir = mediasort.move_all_in_set(set, config['delete_dir'], use_date_directory=False, use_name_directory=False)
    
    del_redis_set(set)
    flash('Saved in {}'.format(dir))
    
  else:
    flash("Nothing")
  return redirect(url_for('index'))

@app.route('/names.json')
def names():
  return json.dumps(['Arthur', 'Henry', 'Cats']);

def make_thumbnail(filename, wh=300):
  from PIL import UnidentifiedImageError
  try:
    return make_thumbnail_pil(filename, wh)
  except UnidentifiedImageError:
    return make_thumbnail_cv2(filename, wh)

def make_thumbnail_pil(filename, wh):
  from PIL import Image
  size = (wh,wh)
  buffered = BytesIO()
  im = Image.open(filename)
  im.thumbnail(size)
  im.save(buffered, format="JPEG")
  return buffered.getvalue()
  
def make_thumbnail_cv2(filename, wh):
  import cv2
  video = cv2.VideoCapture(filename)
  status, image = video.read()

  width = wh
  height = int(width * image.shape[0] / image.shape[1])
  im = cv2.resize(image, (width, height), interpolation = cv2.INTER_AREA)
  is_success, im_buf_arr = cv2.imencode(".jpg", im)
  return im_buf_arr.tobytes() 

  