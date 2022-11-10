import os, exifread, datetime, sys

class MediaItem:
   '''Represents a photo or a video.'''
   
   def __init__(self, path, ):

     self.path = path
     self.orig_filename = os.path.basename(path)
     self.orig_directory = os.path.dirname(path)
     self.dest_filename = self.orig_filename
     # Note that we are not renaming the file, unless there are collisions. I'm not sure why
     self.dest_counter = None
     #self.hash = self.__hash(path)
     self.exif = self.__get_exif()
     
     # This will throw an exception if a timestamp cannot be extracted
     self.timestamp = self.get_timestamp()

     self.id = hash(self.path) & sys.maxsize
     

   def __repr__(self):
     #return "<MediaItem {} {} {}>".format(self.path, self.hash, self.timestamp)
     return "<MediaItem path:{} timestamp:{} id:{}>".format(self.path, self.timestamp, id(self))


   def find_alternate_filename(self):
     if self.dest_counter is None:
       self.dest_counter = 0
     else:
       self.dest_counter += 1
     self.dest_filename = "%s-%04d%s" % (self.orig_filename[:-4], self.dest_counter, self.orig_filename[-4:])
   
   def __lt__(self, other):
     return self.timestamp < other.timestamp
   
   def __hash(self, filename):
     hash_func = hashlib.sha1()
     with open(filename, "rb") as f:
       for chunk in iter(lambda: f.read(4096), b""):
         hash_func.update(chunk)
     return hash_func.hexdigest()
     
   def __getstate__(self):
      state = self.__dict__.copy()
      # Don't pickle exif
      del state["exif"]
      return state

   def __setstate__(self, state):
      self.__dict__.update(state)
      # Adding exif back in
      self.exif = self.__get_exif()

   def get_timestamp(self):
     return datetime.datetime.strptime(self.__read_timestamp(), '%Y:%m:%d %H:%M:%S')
   
   def get_coords(self):
     lat_long = self.__get_tag(['Composite GPSPosition'])
     if lat_long is not None:
       return tuple(lat_long.split(' ', 1))
     
     import exifread
     return exifread.utils.get_gps_coords(self.exif)
   
   def __read_timestamp(self):
     tag = self.__get_tag(['EXIF DateTimeOriginal', 'EXIF DateTimeDigitized', 'Image DateTime', 'QuickTime MediaCreateDate'])
     if tag is None:
       print ("No tag in: {}".format(self.path))
       raise ValueError
     return str(tag)
     
   def __get_tag(self, tags):
     
     for t in tags:
       if t in self.exif:
         return self.exif[t]
     
     return None

   def __get_exif(self):
   
     try:
       exif = self.__exifread(self.path)
     
       if not exif:
         exif = self.__exiftool(self.path)

     except FileNotFoundError:
       print ("Could not open file: {}".format(self.path))
       raise FileNotFoundError
   
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
     
     print (filename)
     
     try: 
       with exiftool.ExifToolHelper() as e:
         data = e.get_metadata(filename)
     except exiftool.exceptions.ExifToolExecuteError:
       print (f"Could not process file: {filename}")
       return
     
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