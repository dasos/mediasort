import logging
from flask import current_app, g
from flask_redis import FlaskRedis
import requests

def get_db():

  if 'redis_client' in g:
    return g.redis_client

  if current_app.testing:
    import fakeredis
    #g.redis_client = fakeredis.FakeRedis()
    g.redis_client = FlaskRedis.from_custom_provider(fakeredis.FakeRedis, current_app, decode_responses=True)
  else:
    # For most Redis requests
    g.redis_client = FlaskRedis(current_app, decode_responses=True)

  return g.redis_client


from PIL import UnidentifiedImageError, Image
from io import BytesIO


def make_thumbnail(filename, wh=300):

  try:
    return make_thumbnail_pil(filename, wh)
  except UnidentifiedImageError:
    logging.getLogger("system.make_thumbnail").info("Could not generate thumbnail")
    return ""

def make_thumbnail_pil(filename, wh):
  size = (wh,wh)
  buffered = BytesIO()
  im = Image.open(filename)
  im.thumbnail(size)
  im.save(buffered, format="JPEG")
  return buffered.getvalue()
  

def get_location(coords):
  
  if not coords:
    return ""
  
  redis_client = get_db()
  
  rounded_coords = round(float(coords[0]), 4), round(float(coords[1]), 4)
  rounded_coords_key = f'coord-{rounded_coords[0]}-{rounded_coords[1]}'
  
  if redis_client.exists(rounded_coords_key):
    result = redis_client.get(rounded_coords_key)
    logging.getLogger("system.get_location").info(f'Pulled {result} from db location cache')
    return redis_client.get(rounded_coords_key)
  
  result = request_location(rounded_coords)
  
  redis_client.set(rounded_coords_key, result)
  logging.getLogger("system.get_location").info(f'Storing {result} in db location cache under {rounded_coords_key}')
  
  return result

def request_location(coords):
  payload = {'lat': coords[0], 'lon': coords[1]}
  
  try:
    r = requests.get('https://photon.komoot.io/reverse', params=payload)
  except Exception:
    logging.getLogger("system.get_location").error('Error resolving coord')
    return ''
  
  if "features" not in r.json() or len(r.json()["features"]) != 1:
    logging.getLogger("system.get_location").warning (f'Could not find location feature in : {r.text}')
    return ""
    
  result = r.json()["features"][0]["properties"]
  
  if "name" in result:
    return result["name"]
  
  if "city" in result:
    return result["city"]
    
  return result


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