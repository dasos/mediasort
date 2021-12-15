import argparse, sys, os, hashlib, datetime, itertools, shutil, re, random

VERSION = "0.0.1"


class NoTag(Exception):
  pass


class MediaItem:
   '''Represents a photo or a video.'''
   
   def __init__(self, path, all_sets=False):
     if path.endswith('.jpg'):
       self.suffix = ".jpg"
     elif path.endswith('.mp4'):
       self.suffix = ".jpg"
     else:
       print ("Not a valid file")
       return
   
     self.path = path
     self.orig_filename = os.path.basename(path)
     self.orig_directory = os.path.dirname(path)
     self.dest_filename = self.orig_filename
     # Note that we are not renaming the file, unless there are collisions. I'm not sure why
     self.dest_counter = None
     #self.hash = self.__hash(path)
     self.exif = self.__get_exif()
     self.timestamp = self.__timestamp()
     self.coords = self.__coords()
     self.id = id(self)

   def __repr__(self):
     #return "<MediaItem {} {} {}>".format(self.path, self.hash, self.timestamp)
     return "<MediaItem path:{} timestamp:{} id:{}>".format(self.path, self.timestamp, id(self))


   def find_alternate_filename(self):
     if self.dest_counter is None:
       self.dest_counter = 0
       self.dest_filename = self.dest_filename[:-4] + '-0000' + self.suffix
     else:
       self.dest_counter += 1
       self.dest_filename = "%s-%04d%s" % (self.dest_filename[:-9], self.dest_counter, self.suffix)
   
   def __lt__(self, other):
     return self.timestamp < other.timestamp
   
   def __hash(self, filename):
     hash_func = hashlib.sha1()
     with open(filename, "rb") as f:
       for chunk in iter(lambda: f.read(4096), b""):
         hash_func.update(chunk)
     return hash_func.hexdigest()


   def __timestamp(self):
     return datetime.datetime.strptime(self.__read_timestamp(), '%Y:%m:%d %H:%M:%S')
   
   def __coords(self):
     lat_long = self.__get_tag(['Composite GPSPosition'])
     if lat_long is not None:
       return tuple(lat_long.split(' ', 1))
     
     import exifread
     return exifread.utils.get_gps_coords(self.exif)
   
   def __read_timestamp(self):
     tag = self.__get_tag(['EXIF DateTimeOriginal', 'EXIF DateTimeDigitized', 'Image DateTime', 'QuickTime MediaCreateDate'])
     if tag is None:
       raise NoTag
     return str(tag)
     
   def __get_tag(self, tags):
     
     for t in tags:
       if t in self.exif:
         return self.exif[t]
     
     return None

   def __get_exif(self):
   
     exif = self.__exifread(self.path)
     
     if not exif:
       exif = self.__exiftool(self.path)
   
     if not exif:
       raise NoTag
     
     return exif
   
   
   def __exifread(self, filename):
     import exifread
     
     with open(filename, 'rb') as f:
       data = exifread.process_file(f, details=False)

     return data
     
   def __exiftool(self, filename):
     import exiftool
     
     with exiftool.ExifTool() as e:
       data = e.get_metadata(filename)
     
     # Turn EXIF:DateTimeOriginal into EXIF DateTimeOriginal
     return {k.replace(":", " "):v for (k,v) in data.items()}
     

   # def __exifread(self, filename, tags=['EXIF DateTimeOriginal', 'EXIF DateTimeDigitized', 'Image DateTime']):
     # import exifread
     
     # with open(filename, 'rb') as f:
       # data = exifread.process_file(f, details=False)

     # for t in tags:
       # if t in data:
         # return str(data[t])
     
     # raise NoTag
   
   # def __exiftool(self, filename, tags=['EXIF:DateTimeOriginal', 'EXIF:DateTimeDigitized', 'QuickTime:CreateDate']):
     # import exiftool
     # with exiftool.ExifTool() as e:
       # data = e.get_metadata(filename)

     # for t in tags:
       # if t in data:
         # return str(data[t])

     # print (dat)
     # raise NoTag


class MediaSet:
    '''Represents a set of MediaItems, x hours apart.'''
    
    def __init__(self, item: MediaItem, gap=2):
      self.gap = gap
      self.start = self.end = self._start = self._end = item.timestamp
      self.__adjust_boundaries(item)
      self.set = [item]
      self.id = id(self)
      self.name = ""
    
    def __adjust_boundaries(self, item):
      self._start = min(item.timestamp - datetime.timedelta(hours=self.gap), self._start)
      self._end = max(item.timestamp + datetime.timedelta(hours=self.gap), self._end)
      
      self.start = min(item.timestamp, self.start)
      self.end = max(item.timestamp, self.end)

    def __recalculate_boundaries(self):
      self.start = self.end = self._start = self._end = random.choice(self.set).timestamp
      [self.__adjust_boundaries(i) for i in self.set]
    
    def __lt__(self, other):
     return self.start < other.start
    
    def set_name(self, name):
      self.name = re.sub('[^\w &]+', '', name).strip()
      
      
    def remove_item(self, item: MediaItem):
      self.set.remove(item)
      self.__recalculate_boundaries()
    
    def add_item(self, item: MediaItem):
      if (item.timestamp < self._start or item.timestamp > self._end):
        return False
      
      self.set.extend([item])
      self.__adjust_boundaries(item)
      return True
      
#    def merge(self, another):
#      self.start = min(another.start, self.start)
#      self.end = max(another.end, self.end)
#      self.set.extend(another.set)


    def sample_filenames(self, number=3):
      return [p.path for p in random.sample(self.set, min(len(self.set), number))]
    
    def date_directory(self):
      return self.start.strftime("%Y/%Y-%b/%Y-%m-%d").strip()
      
      
      
    def __repr__(self):
      return "<MediaSet: {} {} >".format(self.name, ''.join(str(i) for i in self.set))
    
    def __str__(self):
      return "{} in set. Sample filenames: ".format(len(self.set)) + '; '.join(self.sample_filenames())


def get_media(path):
    for dirpath, dirnames, files in os.walk(path):
        for f in files:
            if f.endswith('.jpg') or f.endswith('.mp4'):
                yield os.path.join(dirpath, f)

      
def pairwise(iterable):
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def parse_args():
    parser = argparse.ArgumentParser(description='Move photos or videos based on the EXIF data.')
    parser.add_argument('input_dir')
    parser.add_argument('output_dir')
    parser.add_argument(
            '-d',
            '--dryrun',
            action='store_true',
            default=False)
    parser.add_argument(
            '-v',
            '--version',
            action='version',
            version='photosort v' + VERSION)
    args = parser.parse_args()

    if not os.path.isdir(args.input_dir):
        sys.stderr.write("Invalid directory: %s\n" % args.input_dir)
        sys.exit(1)

    if not os.path.isdir(args.output_dir):
        sys.stderr.write("Invalid directory: %s\n" % args.output_dir)
        sys.exit(1)

    if args.input_dir == args.output_dir:
        sys.stderr.write("Input and output directories need to be different.\n")
        sys.exit(1)
        
    if args.dryrun:
        print("DRY-RUN")

    return args
    
class GetName:
  previous_name = None

  @classmethod
  def ask(cls):
    while True:
      name = input("Name : ")
    
      if (name.lower() == "h"):
        print ("h       print some help")
        print ("s       skip")
        print ("<blank> use previous name")
        continue
    
      if (name == "" and cls.previous_name is None):
        print ("Must provide a name for the first set")
        continue
        
      if (name == "s"):
        return "", "skip"
      
      if (name == ""):
        name = cls.previous_name
      else:
        cls.previous_name = name

      return name, "name"

def create_dir(dir, dryrun=False):
      print (dir)
      
      if (not dryrun):
        os.makedirs(dir, exist_ok=True)
          
      return dir

def move_file(item, folder_name, dryrun=False):

    while os.path.exists(os.path.join(folder_name, item.dest_filename)):
      item.find_alternate_filename()
    
    dest = os.path.join(folder_name, item.dest_filename)
    print ("{} > {}".format(item.path, dest))
    
    if (dryrun):
      return
    
    shutil.move(item.path, dest)

def move_all_in_set(set, output_dir, use_date_directory=True, use_name_directory=True, dryrun=False):
    if (use_date_directory and use_name_directory):
      folder_name = os.path.join(output_dir, "{} {}".format(set.date_directory(), set.name))
    elif (use_date_directory):
      folder_name = os.path.join(output_dir, set.date_directory())
    elif (use_name_directory):
      folder_name = os.path.join(output_dir, set.name)
    else:
      folder_name = output_dir
    create_dir(folder_name, dryrun)
    
    [move_file(item, folder_name, dryrun) for item in set.set]
    
    return folder_name

def load(input_dir, callback = None, all_sets = []):

    print ("Loading data. This may take some time.")
    # Get everything
    
    def upsert_set(item, all_sets):
    
      found = False
      set = None
     
      for s in all_sets:
        found = s.add_item(item)
        if found:
          set = s
          break
     
     
      if not found:
        set = MediaSet(item)
        all_sets.append(set)
        print ("Made new set: {}".format(len(all_sets)))
     
      # Sorting every time since the start of a set may have changed
      all_sets.sort()
      
      return set
    
    def create_sort_send(path):
      # Create the MediaItem
      item = MediaItem(path)
      
      # Put it in a set
      set = upsert_set(item, all_sets)
      
      # Tell people we've done it
      callback(item, set)
    
    all_items = [create_sort_send(path) for path in get_media(input_dir)]

    
    print ("Done. Number of sets: {}".format(len(all_sets)))
    return all_sets


def main():
    args = parse_args()
    
    # Get all the data
    all_sets = load(args.input_dir)

    # Now name the sets
    
    # This loops through a copy of the set, so we can remove items from the original
    #for i in all_sets[:]: 
    for i in all_sets:
      
      print (i)

      name, action = GetName.ask()
      
      if (action == "skip"):
        print ("Skipping")
        #all_sets.remove(i)
        continue
        
      #if (previous_name is not None and name == ""):
      #  i.name = previous_name
        #print ("Merging sets")
        #j.merge(i)
        #all_sets.remove(i)
        #continue
      #else:
      i.set_name(name)
      
      # Move all the files in the set
      move_all_in_set(i, args.output_dir, dryrun=args.dryrun)
      

if __name__ == "__main__":
    sys.exit(main())