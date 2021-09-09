import mediasort
import base64, json
import itertools
import threading

#ImageFile.LOAD_TRUNCATED_IMAGES = True

from io import BytesIO

from flask import Flask, render_template, request, flash, redirect, url_for, make_response

dataLock = threading.Lock()

def create_app():
  app = Flask(__name__)
  app.config['SECRET_KEY'] = 'Zru78eP4YpSbzrQH6sQ57XfQhXFbqGHCdWmX4YkyRT4v9QpK'
  return app

def load_config():

  config = { "input_dir": "/input", "output_dir": "/output", "delete_dir": "/delete", "thumbnails": 21, "suggestions": ["arthur", "henry"] }
  try:
    with open("config.json") as json_file:
      loaded = json.load(json_file)
      config.update(loaded)
  except Exception:
    print ("Could not load config.json file. Defaults will be used")
    
  print(config["input_dir"])
    
  return config

def load_all_sets():
  global all_sets
  global setThread
  
  def load_data():
    global all_sets
    
    # Get all the sets as a list
    with dataLock:
      mediasort.load(config["input_dir"], all_sets)
    
      # Flip into a dict
      #all_sets = {id(x): x for x in set_list}
   
  setThread = threading.Thread(target=load_data)
  setThread.start()


app = create_app()
config = load_config()
all_sets = []
load_all_sets()

@app.route('/')
def index():
  if (all_sets is not None):
    return render_template('index.html', sets=all_sets[:5], thumbnails=config.get('thumbnails'))
  return render_template('nothing.html')

@app.route('/thumbnail/<int:set_index>/<int:photo_id>.jpg')
@app.route('/thumbnail/<int:size>/<int:set_index>/<int:photo_id>.jpg')
def get_thumbnail(set_index, photo_id, size=300):
  #set = get_set(set_index, request.form.get('id'))
  set = all_sets[set_index]
  item = set.set[photo_id]
  thumbnail = make_thumbnail(item.path, size)

  response = make_response(thumbnail)
  response.content_type = 'image/jpeg'
  return response

def get_set(set_id, set_index=False):
  global all_sets
  if (set_index is not False and id(all_sets[set_index]) == set_id):
    return all_sets[set_index]
  
  for s in all_sets:
    if (id(s) == set_id):
      return s
  
  raise Exception("Missing set.  set_id: {}".format(set_id))

@app.route('/remove/<int:set_id>/<int:photo_id>', methods=('POST',))
def delete_from_set(set_id, photo_id):
  global all_sets
  set = get_set(set_id)
  
  item = set.set[photo_id]
  set.remove_item(item)
  
  all_sets.append(mediasort.MediaSet(item))
  all_sets.sort()
  
  flash('Removed {}'.format(item.dest_filename))
  return redirect(url_for('index'))

#@app.route('/', methods=('POST',))
@app.route('/set/<int:set_id>', methods=('POST',))
def post(set_id):
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
    all_sets.remove(set)
    flash('Saved in {}'.format(dir))
    
  # Delete
  elif request.form.get("action") == "delete":
    dir = mediasort.move_all_in_set(set, config['delete_dir'], use_date_directory=False, use_name_directory=False)
    all_sets.remove(set)
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

  