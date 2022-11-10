import argparse, sys, os, hashlib, datetime, itertools, shutil, re, random

VERSION = "0.0.1"


class NoTag(Exception):
  pass


import MediaItem, MediaSet





def get_media(path):
    for dirpath, dirnames, files in os.walk(path):
      for f in files:
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
