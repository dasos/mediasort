from web_app import system, data
import json
import logging

from flask import Blueprint, request, jsonify, current_app
from flask_executor import Executor

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/status")
def get_result():

    redis_client = system.get_db()

    result = {
        # TODO: make this more efficient
        "item_count": len(list(redis_client.scan_iter(match="mediasort:item-*"))),
        "set_count": redis_client.zcount("mediasort:sets", "-inf", "+inf"),
        "status": redis_client.get("mediasort:status"),
    }

    return jsonify(result)


@bp.route("/debug")
def get_debug():

    redis_client = system.get_db()

    items = []
    for name in redis_client.scan_iter(match="mediasort:item-meta-*"):
        items.append({name: redis_client.hgetall(name)})

    sets = []
    for name in redis_client.scan_iter(match="mediasort:set-meta-*"):
        set_id = redis_client.hget(name, "id")
        sets.append(
            {
                "name": redis_client.hgetall(name),
                "items": [
                    name
                    for name in redis_client.zrange(
                        f"mediasort:set-items-{set_id}", 0, -1
                    )
                ],
            }
        )

    result = {
        "items": items,
        "sets": sets,
    }

    return jsonify(result)


@bp.route("/reload")
def reload_data():

    data.clear_db()
    data.populate_db()

    return jsonify(
        data={
            "result": "OK",
        }
    )


@bp.route("/set/<string:action>/<int:set_id>", methods=("POST",))
def move_set(action, set_id):

    logger = logging.getLogger("mediasort.api.move_set")
    redis_client = system.get_db()

    # The function that is executed in a thread
    def actually_move(set, name, testing=False):
        testing = True

        def remove_from_db():
            # Perhaps optimistically, remove the information *before* it is actioned. We don't want to interact with it again. If it goes wrong, it can be rescanned
            logger.info("Removing set information from Redis")
            logger.debug(f"Set id: {set.id}")
            redis_client.zrem("mediasort:sets", set.id)
            redis_client.delete(f"mediasort:set-meta-{set.id}")
            for item_id in redis_client.zrange(f"mediasort:set-items-{set_id}", 0, -1):
                redis_client.delete(f"mediasort:item-meta-{item_id}")
            redis_client.delete(f"mediasort:set-items-{set.id}")

        # With date
        if "save" in action:
            set.set_name(name)
            dir = current_app.config.get("OUTPUT_DIR")
            remove_from_db()
            if action == "save_date":
                set.move(dir, dry_run=testing)
            else:
                set.move(dir, use_date_directory=False, dry_run=testing)

            logger.info(f"Moved set: {set}")

        # Delete
        elif action == "delete":
            dir = current_app.config.get("DELETE_DIR")
            remove_from_db()
            set.move(
                dir, use_date_directory=False, use_name_directory=False, dry_run=testing
            )

            logger.info("Moved set to delete directory")

        else:
            logger.error("No command")

    set = data.get_set(set_id, store=True)
    if set is None:
        logger.warning(f"Could not find set id: {set_id}")
        return jsonify(data={"error": "Could not find set"})

    logger.debug(f"Moving set: {set}")
    name = str(request.form.get("name"))

    if "save" in action:
        if name:
            # Adding the name as a suggestion
            redis_client.sadd("mediasort:suggestions", name)
        else:
            return jsonify(data={"error": "You must provide a name to save"}), 400

    if current_app.testing:
        actually_move(set, name, True)
    else:
        logger.info("Starting new thread for load")
        executor = Executor(current_app)
        executor.submit(actually_move, set, name)

    return jsonify(
        data={
            "result": "OK",
        }
    )


@bp.route("/suggestions")
def suggestions():
    redis_client = system.get_db()
    return json.dumps(list(redis_client.smembers("mediasort:suggestions")))
