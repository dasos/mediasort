import os, logging
from MediaItem import MediaItem
from MediaSet import MediaSet

def get_media(path):
  '''Finds all the fields in a particular directory'''
  for dirpath, dirnames, files in os.walk(path):
    for f in files:
      yield os.path.join(dirpath, f)

def load(input_dir, all_sets = []):
  '''Reads the files, and organises them into sets. 
  Then yield each that a new item has been processed'''

  l = logging.getLogger("mediasort.MediaFiles.load")
  l.info("Loading data. This may take some time.")
  # Get everything
  
  def upsert_set(item, all_sets):
    '''Loops through all the sets, finding one that will fit.
    If it can't find one, it creates one'''
  
    found = False
    set = None
   
    for s in all_sets:
      found = s.check_item_fits(item)
      if found:
        s.add_item(item)
        set = s
        break
   
    # Creates a new set
    if not found:
      set = MediaSet(item)
      all_sets.append(set)
      l.info("Made new set: {}".format(len(all_sets)))
   
    # Sorting every time since the start of a set may have changed
    all_sets.sort()
    
    return set
  
  def create_sort_send(path):
    l.debug(f"Loading path: {path}")
    # Create the MediaItem
    try:
      item = MediaItem(path)
    except Exception:
      l.warning(f"Unable to add file: {path}")
      return None, None
    
    # Ignore invalid files
    
    # Put it in a set
    set = upsert_set(item, all_sets)
    
    # Tell people we've done it
    return item, set
  
  for path in get_media(input_dir):
    item, set = create_sort_send(path)
    if item is not None:
      yield item, set

  
  l.info("Done. Number of sets: {}".format(len(all_sets)))
