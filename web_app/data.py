from codetiming import Timer

import logging

from flask import current_app
from flask_executor import Executor
from datetime import datetime

from web_app import system

import MediaFiles
from MediaItem import MediaItem
from MediaSet import MediaSet, MediaSetStore


def clear_db():

    message = (
        "*************************** DELETING FROM DB! ***************************"
    )
    logger = logging.getLogger("mediasort.system.clear_db")
    logger.warning(message)

    redis_client = system.get_db()

    # Save some stuff
    suggestions = []
    locations = {}

    if current_app.config.get("KEEP_SUGGESTIONS"):
        suggestions = list(redis_client.smembers("mediasort:suggestions"))
    if current_app.config.get("KEEP_LOCATIONS"):
        location_keys = redis_client.scan_iter(match="mediasort:coord-*")
        for key in location_keys:
            locations[key] = redis_client.get(key)

    if current_app.config.get("FLUSH"):
        logger.warning("Flushing DB")
        redis_client.flushdb()
    else:
        logger.warning("Deleting from DB")
        for name in redis_client.scan_iter(match="mediasort:*"):
            redis_client.delete(name)

    # Put it back
    [redis_client.sadd("mediasort:suggestions", s) for s in suggestions]
    [redis_client.set(key, value) for key, value in locations.items()]


def populate_db(force=False):

    logger = logging.getLogger("mediasort.system.populate_db")

    redis_client = system.get_db()

    def load_data(input_dir):

        for item, set in MediaFiles.load(input_dir):

            save_set(set)
            save_item(item, set)

        logger.info("Setting status as done.")
        redis_client.set("mediasort:status", "done")

    #  status = redis_client.get('status')
    #  if status == "loading":
    #    logger.info ("Status is loading")
    #    if force is False:
    #      return False

    redis_client.set("mediasort:status", "loading")

    if current_app.testing:
        load_data(current_app.config.get("INPUT_DIR"))
    else:
        logger.info("Starting new thread for load")
        executor = Executor(current_app)
        executor.submit(load_data, current_app.config.get("INPUT_DIR"))
    return


def save_set(set):
    """Saves a set to redis. Will also overwrite if needed."""

    redis_client = system.get_db()
    logger = logging.getLogger("mediasort.system.save_set")

    # Adds the set into a sorted set, which has the start time as the score
    redis_client.zadd("mediasort:sets", {set.id: set.start.timestamp()})

    # Adds the set into a hash set. This stores a bit of information about the set, which reduces recalculation
    redis_client.hset(
        f"mediasort:set-meta-{set.id}",
        mapping={
            "length": set.length,
            "start": int(set.start.timestamp()),
            "end": int(set.end.timestamp()),
            "id": set.id,
        },
    )

    logger.debug(f"Saving set: {set.id}")


def save_item(item, set):
    """Saves an item to redis."""

    redis_client = system.get_db()
    logger = logging.getLogger("mediasort.system.save_item")

    # Adds the item into a hash set. We'll store some attributes about the item. When we want the media item back,
    # we set them back to what they were it
    # It is perhaps superfluous to add the ID, but we'll pop it in for testing purposes
    redis_client.hset(
        f"mediasort:item-meta-{item.id}",
        mapping={
            "path": item.path,
            "timestamp": item.timestamp.timestamp(),
            "id": item.id,
        },
    )

    # Adds the item into a sorted set specific to the set. The timestamp of the item is the score
    # We use this to find the right items to add them back in to the set
    redis_client.zadd(
        f"mediasort:set-items-{set.id}", {item.id: item.timestamp.timestamp()}
    )

    logger.debug(f"Inserting item id: {item.id} in to set: {set.id}")


def remove_set(set):
    """Removes all information about a set from Redis"""
    redis_client = system.get_db()
    logger = logging.getLogger("mediasort.system.remove_set")
    logger.debug(f"Set id: {set.id}")
    redis_client.zrem("mediasort:sets", set.id)
    redis_client.delete(f"mediasort:set-meta-{set.id}")
    for item_id in redis_client.zrange(f"mediasort:set-items-{set.id}", 0, -1):
        redis_client.delete(f"mediasort:item-meta-{item_id}")
    redis_client.delete(f"mediasort:set-items-{set.id}")


def remove_item(item, set):
    """Remove a single item. It does not update the set information, so the set will need
    to be resaved to update it."""
    redis_client = system.get_db()
    logger = logging.getLogger("mediasort.system.remove_set")
    logger.debug(f"Removing item id: {item.id}")
    redis_client.delete(f"mediasort:item-meta-{item.id}")
    redis_client.zrem(f"mediasort:set-items-{set.id}", item.id)


def get_item_path(item_id):
    """Returns just the path of the item, used in thumbnail creation and in recreating the item"""
    redis_client = system.get_db()
    return redis_client.hget(f"mediasort:item-meta-{item_id}", "path")


@Timer(name="get_item", text="{name}: {:.4f} seconds")
def get_item(item_id):
    """Get a single item by its id"""

    logger = logging.getLogger("mediasort.system.get_item")

    path = get_item_path(item_id)
    try:
        item = MediaItem(path)
        return item
    except Exception:
        logger.error(f"File has gone away: {path}")
        raise


@Timer(name="get_set", text="{name}: {:.4f} seconds")
def get_set(set_id, limit=0, from_end=False, store=False, no_meta=False):
    """Gets a single set by id, and, by default, all the items in it"""

    logger = logging.getLogger("mediasort.system.get_set")

    logger.debug(f"Trying to get set_id: {set_id}")

    redis_client = system.get_db()

    if store is False:
        set = MediaSet()
    else:
        set = MediaSetStore()

    start = 0
    end = limit - 1

    if from_end:
        start = 0 - limit
        end = -1

    for item_id in redis_client.zrange(f"mediasort:set-items-{set_id}", start, end):
        try:
            item = get_item(item_id)

            # By default, it'll regenerate an id. We don't want that
            item.id = item_id
        except Exception:
            logger.warn("Skipping item in set")
            continue

        set.add_item(item)

    # Each time you add an item, you set the length. So we need to do it at the end.
    # This will also set the set id
    # If you don't want to do this (for performance), set no_meta to true
    if no_meta is False:
        set = set_from_meta(set_id, set)

    return set


def top_tail_set(set_id, limit):
    """Gets the start and end items of the set, in a "top and tail" style. Ish."""

    # Since we are doing it twice, we will only do half each time
    # TODO: account for odd values of limit
    num_items = int(limit / 2)

    # Using no_meta since we'll do it ourselves later
    top = get_set(set_id, num_items, store=True, no_meta=True)
    tail = get_set(set_id, num_items, from_end=True, store=True, no_meta=True)

    # Put everything from tail into top (assuming not already there)
    for x in tail.get_items():
        if not top.check_item_exists(x):
            top.add_item(x)

    # Set the length, start, end, etc, from the meta data stored in Redis
    top = set_from_meta(set_id, top)
    return top


def get_empty_set(set_id, limit=-1, from_end=False, store=False):
    """Gets a single set by id, with no files, but with the right boundary and length"""

    set = set_from_meta(set_id)

    return set


def set_from_meta(set_id, s=MediaSet()):
    """Sets important items about the set from the metadata stored in Redis"""

    logger = logging.getLogger("mediasort.system.set_from_meta")

    redis_client = system.get_db()
    meta = redis_client.hgetall(f"mediasort:set-meta-{set_id}")

    logger.debug(f"Updating set with metadata: {meta}")

    s.start = datetime.fromtimestamp(int(meta["start"]))
    s.end = datetime.fromtimestamp(int(meta["end"]))
    s.length = int(meta["length"])
    s.id = meta["id"]
    return s


@Timer(name="get_top_tail_sets", text="{name}: {:.4f} seconds")
def get_top_tail_sets(num_sets=5, max_items=10, reverse=False):
    """Gets some sets that contain some items in a "top and tail" fashion"""
    redis_client = system.get_db()

    sets = []

    for set_id in redis_client.zrange(
        "mediasort:sets", start=0, end=num_sets, desc=reverse
    ):

        # sets.append(get_set(set_id, max_items, store=True))
        sets.append(top_tail_set(set_id, max_items))

    return sets


@Timer(name="remove_item_from_set", text="{name}: {:.4f} seconds")
def remove_item_from_set(item_id, set_id):
    """Removes a specific item from a set. Returns the new set"""
    logger = logging.getLogger("mediasort.data.remove_item_from_set")
    logger.debug(f"Looking for item id: {item_id} in set id: {set_id}")

    set = get_set(set_id, store=True)
    if set is None:
        raise Exception(f"Could not find set id: {set_id}")

    item = None

    # Finding the item in the set
    item = set.get_item_by_id(item_id)

    if item is None:
        raise Exception(f"Could not find item id: {item_id} in set id: {set_id}")

    set.remove_item(item)  # Remove the item from the set
    remove_item(item, set)  # Remove the old item information from Redis
    save_set(
        set
    )  # Resaves the set, since the start, length and other information may change

    new_set = MediaSetStore(item)  # Creates a new MediaSet with the item
    save_set(new_set)  # Saves the new set
    save_item(item, new_set)  # Re-add the item, but this time with the new set info

    return new_set
