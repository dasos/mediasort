INPUT_DIR = "/input"
OUTPUT_DIR = "/output"
DELETE_DIR = "/delete"
SETS_SHOWN = 3
SUMMARY_ITEMS = 6
MAX_ITEMS = 200
DEBUG_LEVEL = "INFO"
DRY_RUN = True
# If true, no file system writes will happen.
KEEP_SUGGESTIONS = True
# If true, saves the type-ahead suggestions. Otherwise they go when the refresh happens
FLUSH = False
# If true, flush (empty) the database. Otherwise it seletes all the keys prefixed with 'mediasort:' You probably want to do this if you start seeing timeouts when the refresh is happening
