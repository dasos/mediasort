import argparse, sys, os, hashlib, datetime, itertools, shutil, re, random

VERSION = "0.0.1"


class NoTimestamp(Exception):
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
     self.timestamp = self.__timestamp(path)
     self.id = id(self)
     
     if all_sets is not False:
       self.__set_set(all_sets);
     
   def __set_set(self, all_sets):
     done = False
     
     for s in all_sets:
        done = s.add_item(self)
        if done:
          break
     
     if not done:
       all_sets.append(MediaSet(self))
       print ("Made new set: {}".format(len(all_sets)))
     
     all_sets.sort()

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


   def __timestamp(self, filename):
     return datetime.datetime.strptime(self.__read_timestamp(filename), '%Y:%m:%d %H:%M:%S')
   
   def __read_timestamp(self, filename):
     try:
       result = self.__exifread(filename)
     except NoTimestamp:
       result = self.__exiftool(filename)
     return result
   
   def __exifread(self, filename):
     import exifread
     
     with open(filename, 'rb') as f:
       tags = exifread.process_file(f, details=False)

     if 'EXIF DateTimeOriginal' in tags:
       return str(tags['EXIF DateTimeOriginal'])
     elif 'EXIF DateTimeDigitized' in tags:
       return str(tags['EXIF DateTimeDigitized'])
     elif 'Image DateTime' in tags:
       return str(tags['Image DateTime'])
     
     raise NoTimestamp
   
   def __exiftool(self, filename):
     import exiftool
     with exiftool.ExifTool() as e:
       metadata = e.get_metadata(filename)
       if 'EXIF:DateTimeOriginal' in metadata:
         return str(metadata['EXIF:DateTimeOriginal'])
       elif 'EXIF:DateTimeDigitized' in metadata:
         return str(metadata['EXIF:DateTimeDigitized'])
       elif 'QuickTime:CreateDate' in metadata:
         return str(metadata['QuickTime:CreateDate'])
       else:
         print (metadata)
         raise MissingTimestampError


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

def load(input_dir, all_sets = []):

    print ("Loading data. This may take some time.")
    # Get everything
    all_items = [MediaItem(path, all_sets) for path in get_media(input_dir)]
    
    print ("Done")
    return
    
    all_items = sorted([MediaItem(path) for path in get_media(input_dir)])
    
    print ("\nNumber of items: {}".format(len(all_items)))
    
    # Then put them in sets
    all_sets = []
    set = None
    for i in all_items:
      if (set is None or not set.add_item(i)):
        set = MediaSet(i)
        all_sets.append(set)

    print ("Done loading")
    
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