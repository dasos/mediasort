import os
import logging
from MediaItem import MediaItem
def get_media(path):
    """Finds all the fields in a particular directory"""
    for dirpath, dirnames, files in os.walk(path):
        for f in files:
            yield os.path.join(dirpath, f)


def load(input_dir):
    """Reads the files and yields MediaItems. Sets are created client-side now."""

    logger = logging.getLogger("mediasort.MediaFiles.load")
    logger.info("Loading data. This may take some time.")

    for path in get_media(input_dir):
        logger.debug(f"Loading path: {path}")
        try:
            item = MediaItem(path)
        except Exception:
            logger.warning(f"Unable to add file: {path}")
            continue

        yield item
