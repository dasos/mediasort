from MediaItem import MediaItem
from MediaSet import MediaSet
import datetime
  
def test_set():

  i = MediaItem("images/leaf.jpg")
  s = MediaSet(i)
  
  assert s.length == 1
  
  
def test_add():

  i1 = MediaItem("images/forest.jpg")
  s = MediaSet(i1)
  i2 = MediaItem("images/calculator.jpg")
  s.add_item(i2)

  assert s.length == 2
  
def test_reject():

  i1 = MediaItem("images/leaf.jpg")
  s = MediaSet(i1)
  i2 = MediaItem("images/forest.jpg")

  # Because i2 is too far away from i1 in time
  assert s.check_item_fits(i2) == False

def test_add_wider_gap():

  i1 = MediaItem("images/leaf.jpg")
  s = MediaSet(i1, 4)
  i2 = MediaItem("images/forest.jpg")
  result = s.add_item(i2)

  assert s.length == 2 and result is True
  
def test_remove():

  i1 = MediaItem("images/forest.jpg")
  s = MediaSet(i1)
  i2 = MediaItem("images/calculator.jpg")
  s.add_item(i2)

  assert s.length == 2

  s.remove_item(i2)
  
  assert s.length == 1

def test_equivalence():

  i = MediaItem("images/forest.jpg")
  s1 = MediaSet(i)
  s2 = MediaSet(i)

  assert s1 == s2


def test_timestamp():

  i1 = MediaItem("images/forest.jpg")
  s = MediaSet(i1)

  assert s.start == (datetime.datetime(2022, 1, 1, 10, 0)) and s.end == (datetime.datetime(2022, 1, 1, 10, 0))

def test_timestamp_string():

  i1 = MediaItem("images/forest.jpg")
  s = MediaSet(i1)

  assert str(s.start) == '2022-01-01 10:00:00' and str(s.end) == '2022-01-01 10:00:00'

def test_boundary_expand():

  i1 = MediaItem("images/forest.jpg")
  s = MediaSet(i1, 3)
  i2 = MediaItem("images/leaf.jpg")
  s.add_item(i2)

  assert str(s._start) == '2022-01-01 07:00:00' and str(s._end) == '2022-01-01 16:00:00'
  
def test_boundary_contract():

  i1 = MediaItem("images/forest.jpg")
  s = MediaSet(i1, 3)
  i2 = MediaItem("images/leaf.jpg")
  s.add_item(i2)
  s.remove_item(i2)

  assert str(s._start) == '2022-01-01 07:00:00'
  assert str(s._end) == '2022-01-01 13:00:00'
  
  s.add_item(i2)
  s.remove_item(i1)

  assert str(s._start) == '2022-01-01 10:00:00'
  assert str(s._end) == '2022-01-01 16:00:00'
  
