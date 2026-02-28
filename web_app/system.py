import logging
from flask import current_app, g
import requests
from PIL import UnidentifiedImageError, Image, ImageOps
from io import BytesIO
import static_ffmpeg
import ffmpeg
from web_app import db


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

    rounded_coords = round(float(coords[0]), 4), round(float(coords[1]), 4)
    conn = db.get_db()

    cached = conn.execute(
        "SELECT location FROM location_cache WHERE lat = ? AND lon = ?",
        (rounded_coords[0], rounded_coords[1]),
    ).fetchone()
    if cached is not None:
        result = cached["location"]
        logging.getLogger("mediasort.system.get_location").info(
            f"Pulled {result} from db location cache"
        )
        return result

    result = request_location(rounded_coords)

    if result != "":
        logging.getLogger("mediasort.system.get_location").info(
            f"Storing {result} in db location cache under {rounded_coords}"
        )
        conn.execute(
            "INSERT OR REPLACE INTO location_cache (lat, lon, location) VALUES (?, ?, ?)",
            (rounded_coords[0], rounded_coords[1], result),
        )
        conn.commit()

    return result


def request_location(coords):
    l = logging.getLogger("mediasort.system.request_location")

    api_key = current_app.config.get("GEOAPIFY_API_KEY")
    if not api_key:
        l.warning("Missing GEOAPIFY_API_KEY; skipping reverse geocode lookup")
        return ""

    payload = {
        "lat": coords[0],
        "lon": coords[1],
        "format": "json",
        "apiKey": api_key,
    }

    try:
        r = requests.get("https://api.geoapify.com/v1/geocode/reverse", params=payload)
    except Exception:
        l.error("Error resolving coord")
        return ""

    if r.status_code != 200:
        l.warning(f"Reverse geocode error: {r.status_code} {r.text}")
        return ""

    try:
        data = r.json()
    except Exception:
        l.error(f"Couldn't parse JSON: {r.text}")
        return ""

    if "results" not in data or len(data["results"]) == 0:
        l.warning(f"Could not find location result in: {r.text}")
        return ""

    result = data["results"][0]

    l.debug(f"Looked up: {payload}. Complete result: {r.text}")

    if "address_line1" in result and result["address_line1"]:
        return result["address_line1"]

    if "formatted" in result and result["formatted"]:
        return result["formatted"]

    if "name" in result and result["name"]:
        return result["name"]

    l.error(f"Could not find useful features in: {r.text}")

    return ""
