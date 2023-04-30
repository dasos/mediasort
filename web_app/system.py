import logging
from flask import current_app, g
from flask_redis import FlaskRedis
import requests
from PIL import UnidentifiedImageError, Image, ImageOps
from io import BytesIO
import static_ffmpeg
from ffmpeg import FFmpeg

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

def make_thumbnail_ffmpeg(filename, wh):
  static_ffmpeg.add_paths(True) # If ffmpeg doesn't exist, get a version
  ffmpeg = (
      FFmpeg(executable='static_ffmpeg')
      .input(filename)
      .output(
          "pipe:1",
          r=2, # frames per sec
          t=10, # max length
          f="webp",
          vf=f"scale={wh}:-2",
      )
  )

  @ffmpeg.on("stderr")
  def on_stderr(line):
    print(line)
  
  try:
    return ffmpeg.execute(), "image/webp"
  except Exception as e:
     print (e)
     print ("FFMPEG error")
  

def make_thumbnail_pil(filename, wh):
    size = (wh, wh)
    buffered = BytesIO()
    
    im = Image.open(filename)
    if (wh > 500): # A poor rule of thumb
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

    redis_client.set(rounded_coords_key, result)
    logging.getLogger("mediasort.system.get_location").info(
        f"Storing {result} in db location cache under {rounded_coords_key}"
    )

    return result


def request_location(coords):
    payload = {"lat": coords[0], "lon": coords[1]}

    try:
        r = requests.get("https://photon.komoot.io/reverse", params=payload)
    except Exception:
        logging.getLogger("mediasort.system.get_location").error(
            "Error resolving coord"
        )
        return ""

    if "features" not in r.json() or len(r.json()["features"]) != 1:
        logging.getLogger("mediasort.system.get_location").warning(
            f"Could not find location feature in : {r.text}"
        )
        return ""

    result = r.json()["features"][0]["properties"]

    if "name" in result:
        return result["name"]

    if "city" in result:
        return result["city"]

    return result
