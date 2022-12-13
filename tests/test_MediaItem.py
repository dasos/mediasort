from MediaItem import MediaItem
from MediaSet import MediaSet
import datetime


def test_load():

    i = MediaItem("images/leaf.jpg")
    assert i.orig_filename == "leaf.jpg"


def test_exifread():

    i = MediaItem("images/leaf.jpg")
    assert i.timestamp == (datetime.datetime(2022, 1, 1, 13, 0))


def test_coords():
    i = MediaItem("images/leaf.jpg")
    assert i.get_coords() == (51.50084130000768, -0.14298782563424842)
