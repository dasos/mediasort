from MediaItem import MediaItem
from MediaSet import MediaSet
import datetime

def test_load():

  i = MediaItem("images/leaf.jpg")
  assert i.orig_filename == "leaf.jpg"

def test_exifread():

  i = MediaItem("images/leaf.jpg")
  assert i.timestamp == (datetime.datetime(2022, 1, 1, 13, 0))
  
