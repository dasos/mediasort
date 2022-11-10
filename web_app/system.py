from flask import current_app, g
from flask_redis import FlaskRedis

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
    logger.info("Could not generate thumbnail")
    return ""

def make_thumbnail_pil(filename, wh):
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