import logging
from flask import current_app, g
from flask_redis import FlaskRedis
import requests
from PIL import UnidentifiedImageError, Image, ImageOps
from io import BytesIO
import static_ffmpeg
import ffmpeg

def get_db():

    if "redis_client" in g:
        return g.redis_client

    logger = logging.getLogger("mediasort.system.get_db")

    if current_app.testing or current_app.config.get("FAKE_REDIS") is True:
        logger.info("Using fake redis. Each request will be as new!")
        import fakeredis

        # g.redis_client = fakeredis.FakeRedis()
        g.redis_client = FlaskRedis.from_custom_provider(
            fakeredis.FakeRedis, current_app, decode_responses=True
        )
    else:
        # For most Redis requests. It uses the REDIS_URL config property automatically
        g.redis_client = FlaskRedis(current_app, decode_responses=True)

    return g.redis_client


def make_thumbnail(filename, wh=300):

    l = logging.getLogger("mediasort.system.make_thumbnail")

    try:
        return make_thumbnail_pil(filename, wh)
    except UnidentifiedImageError:
        
      try:
        l.warning("Falling to ffmpeg for filename")
        return make_thumbnail_ffmpeg(filename, wh)
      except Exception as e:

        l.info("Could not generate thumbnail")
        l.debug(e)
    
    return "", ""

# I don't think the equivilent in static_ffmpeg works
def load_ffmpeg():
  import shutil
  l = logging.getLogger("mediasort.system.load_ffmpeg")
  l.info("Checking for FFMPEG")
  
  if shutil.which("ffmpeg") is None:
    l.warn("Could not find FFMPEG")
    static_ffmpeg.add_paths()
  else:
    l.info("Found FFMPEG")

def make_thumbnail_ffmpeg(filename, wh):
  
  if "ffmpeg" not in g:
    load_ffmpeg()
    g.ffmpeg = True
    
  if wh > current_app.config.get("THUMBNAIL_SIZE"):
    clip_length = current_app.config.get("DETAIL_VIDEO_LENGTH")
  else:
    clip_length = current_app.config.get("THUMBNAIL_VIDEO_LENGTH")

  out, _ = (
    ffmpeg
    .input(filename)
    .trim(duration=clip_length)
    .filter('scale', wh, -12)
    .filter('fps', fps=2, round='up')
    .output('pipe:', format='webp')
    .run(capture_stdout=True)
  )
  
  return out, "image/webp"
  

def make_thumbnail_pil(filename, wh):
    size = (wh, wh)
    buffered = BytesIO()
    
    im = Image.open(filename)
    if wh > current_app.config.get("THUMBNAIL_SIZE"):
      im.thumbnail(size) # Keeps aspect ratio, with no crops
    else:
      im = ImageOps.fit(im, size) # Crops, will be square
    
    im.save(buffered, format="JPEG")
    return buffered.getvalue(), "image/jpeg"


def get_location(coords):

    if not coords:
        return ""

    redis_client = get_db()

    rounded_coords = round(float(coords[0]), 4), round(float(coords[1]), 4)
    rounded_coords_key = f"mediasort:coord-{rounded_coords[0]}-{rounded_coords[1]}"

    if redis_client.exists(rounded_coords_key):
        result = redis_client.get(rounded_coords_key)
        logging.getLogger("mediasort.system.get_location").info(
            f"Pulled {result} from db location cache"
        )
        return redis_client.get(rounded_coords_key)

    result = request_location(rounded_coords)

    if result != "":
      logging.getLogger("mediasort.system.get_location").info(
          f"Storing {result} in db location cache under {rounded_coords_key}"
      )
      redis_client.set(rounded_coords_key, result)
    
    return result


def request_location(coords):
    l = logging.getLogger("mediasort.system.get_location")

    payload = {"lat": coords[0], "lon": coords[1]}

    try:
        r = requests.get("https://photon.komoot.io/reverse", params=payload)
    except Exception:
        l.error(
            "Error resolving coord"
        )
        return ""

    if "features" not in r.json() or len(r.json()["features"]) != 1:
        l.warning(
            f"Could not find location feature in: {r.text}"
        )
        return ""

    result = r.json()["features"][0]["properties"]
    
    l.debug(
            f"Looked up: {payload}. Complete result: {r.text}"
        )

    if "name" in result:
        return result["name"]

    if "city" in result:
        return result["city"]
        
    l.error(f"Could not find name or city in: {r.text}")

    return ""
