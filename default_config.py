INPUT_DIR = "/input"
OUTPUT_DIR = "/output"
DELETE_DIR = "/delete"
DB_PATH = "/config/mediasort.db"
SET_GAP_HOURS = 2
SETS_SHOWN = 3
SUMMARY_ITEMS = 6
ITEMS_PER_PAGE = 20
THUMBNAIL_SIZE = 300
# The width of the thumbnail
THUMBNAIL_VIDEO_LENGTH = 5
# How long a video will be trimmed to, in seconds, in the main page
DETAIL_VIDEO_LENGTH = 60
# How long a video will be when viewing it individually
DETAIL_SIZE = 1200
# The width of the bigger detail picture
MAX_ITEMS = 200
DEBUG_LEVEL = "INFO"
DRY_RUN = True
# If true, no file system writes will happen.
KEEP_SUGGESTIONS = True
# If true, saves the type-ahead suggestions. Otherwise they go when the refresh happens
KEEP_LOCATIONS = True
# If true, saves the locations. Otherwise they go when the refresh happens
FLUSH = False
# If true, flush (empty) the database. Otherwise it selects all the keys prefixed with 'mediasort:' and deletes them individually. You probably want to do this if you start seeing timeouts when the refresh is happening, but really don't do it if you share the DB with anything
