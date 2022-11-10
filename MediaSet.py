import MediaItem, datetime, random

class MediaSet:
  '''Represents a set of MediaItems, x hours apart. The set is actually a dict of filenames and timestamps'''
  
  def __init__(self, item: MediaItem, gap=2):
    self.gap = gap
    self.start = self.end = self._start = self._end = item.timestamp
    self.set = {item.path : item.timestamp}
    self.__adjust_boundaries(item.timestamp)
    self.id = id(self)
    self.name = ""
  
  def __adjust_boundaries(self, t):
    """ Takes in a timestamp and sets the boundaries appropriately """
    # The earliest time that this set will allow
    self._start = min(t - datetime.timedelta(hours=self.gap), self._start)
    # The latest time that this set will allow
    self._end = max(t + datetime.timedelta(hours=self.gap), self._end)
    
    self.start = min(t, self.start)
    self.end = max(t, self.end)
    
    self.length = len(self.set)

  def __recalculate_boundaries(self):
    """ Loops through every item to update the boundaries """
    timestamps = list(self.set.values())
    self.start = self.end = self._start = self._end = random.choice(timestamps)
    [self.__adjust_boundaries(i) for i in timestamps]

  def set_name(self, name):
    self.name = re.sub(r'[^\w &-]+', '', name).strip()
  
  def __lt__(self, other):
   return self.start < other.start
  
  def __eq__(self, other):
    if self.length != other.length:
      return False
    
    return self.set == other.set
  
  def remove_item(self, item: MediaItem):
    self.set.pop(item.path)
    self.__recalculate_boundaries()
  
  def check_item_fits(self, item: MediaItem):
    # This will reject the item if it falls outside of the boundaries
    return (item.timestamp > self._start and item.timestamp < self._end)
    
  
  def add_item(self, item: MediaItem):
  
    self.set.update({item.path : item.timestamp})
    self.__adjust_boundaries(item.timestamp)
    return True
    
#    def merge(self, another):
#      self.start = min(another.start, self.start)
#      self.end = max(another.end, self.end)
#      self.set.extend(another.set)



  
  def date_directory(self):
    return self.start.strftime("%Y/%Y-%m/%Y-%m-%d").strip()
    
    
    
  def __repr__(self):
    return "<MediaSet: {} {} >".format(self.name, ''.join(str(i) for i in self.set))
  
  def __str__(self):
    return f'Length of set: {len(self.set)}. Boundary: {self._start} - {self._end}. Actual: {self.start} - {self.end}'
    return "{} in set. Sample filenames: ".format(len(self.set)) + '; '.join(self.sample_filenames())

## TODO: needs to actually be built...
class MediaSetStore (MediaSet):
  '''Builds on the MediaSet. Actually stores the MediaItems themselves as well in the set'''
  def __init__(self, item: MediaItem, gap=2):
    super().__init__(item, gap)
    self.set = [item]
    
  def sample_filenames(self, number=3):
    return [p.path for p in random.sample(self.set, min(len(self.set), number))]