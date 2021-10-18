import mediasort
import base64, json
import itertools
import os
#ImageFile.LOAD_TRUNCATED_IMAGES = True
from io import BytesIO
from flask import Flask, render_template, request, flash, redirect, url_for, make_response, session, jsonify
from flask_session import Session
from flask_executor import Executor

#
# Set up Flask
#

app = Flask(__name__)
if os.environ.get("SECRET_KEY") is not None:
  app.secret_key = os.environ.get("SECRET_KEY")
else:
  app.secret_key = os.urandom(16)

app.config['SESSION_TYPE'] = 'filesystem'
Session(app)  

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


all_sets = []

def load_sets(force = False):
  global all_sets

  def load_data(input_dir):
    # Get all the sets as a list
    mediasort.load(config["input_dir"], all_sets) # note the global variable
    return all_sets
  
  #if 'load' not in executor.futures._futures
  
  if 'sets' not in session or force is True:
    session['sets'] = all_sets = [] # shall I move this?
    future = executor.submit_stored('load', load_data, config["input_dir"])
    session['status'] = "in_progress"
    
  elif executor.futures.running('load'):
    # This allows us to see the progress of the load
    session['sets'] = all_sets
    session['status'] = "in_progress"
    
  elif executor.futures.done('load'):
    future = executor.futures.pop('load')
    #session['sets'] = future.result()
    session['sets'] = all_sets
    session['status'] = "done"

  

config = load_config()

#
# Generates the basic HTML page
#

@app.route('/')
def index():

  #if 'sets' not in session or len(session['sets']) == 0:
  load_sets()
  
  #future = executor.futures.pop('load')
  if session['sets'] is not None:
    return render_template('index.html', sets=session['sets'][:5], num_thumbnails=config.get('thumbnails'), base_path=config.get("input_dir"))
    
  return render_template('nothing.html')

@app.route('/status')
def get_result():
  load_sets()
  return jsonify({'status': session['status']})
  
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

#
# Searches through the array to find the right set. Note the array may change size, and alter dynamically
# TODO: another approach?...
#

def get_set(set_id):
  load_sets()
  
  for s in session['sets']:
    if (s.id == set_id):
      return s
  
  raise Exception("Missing set. set_id: {}".format(set_id))


def get_item(set, item_id):
  if isinstance(set, mediasort.MediaSet):
    return [x for x in set.set if x.id == item_id][0]
  
  return get_item(get_set(set), item_id)

#
# Removes an item from a set.
#

@app.route('/remove/<int:set_id>/<int:photo_id>', methods=('POST',))
def delete_from_set(set_id, photo_id):
  
  if session['status'] == "in_progress":
    flash('Data is still loading', 'warning')
    return redirect(url_for('index'))
    
  load_sets()
  set = get_set(set_id)
  
  item = get_item(set_id, photo_id)
  set.remove_item(item)
  
  session['sets'].append(mediasort.MediaSet(item))
  session['sets'].sort()
  
  flash('Removed {}'.format(item.dest_filename))
  return redirect(url_for('index'))

#
# Gets more thumbnails for a set
#
@app.route('/set/<int:set_id>')
def more_thumbnails(set_id):
  set = get_set(set_id)
  if (not set):
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

  if session['status'] is "in_progress":
    flash('Data is still loading', 'warning')
    return redirect(url_for('index'))


  set = get_set(set_id)
  if (not set):
    flash('Could not find set. Reloading the page', 'warning')
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
    
    session['sets'].remove(set)
    flash('Saved in {}'.format(dir))
    
  # Delete
  elif request.form.get("action") == "delete":
    dir = mediasort.move_all_in_set(set, config['delete_dir'], use_date_directory=False, use_name_directory=False)
    
    session['sets'].remove(set)
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

  