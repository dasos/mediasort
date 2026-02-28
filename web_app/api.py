from web_app import data
import json
import logging

from flask import Blueprint, request, jsonify, current_app
from flask_executor import Executor

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/status")
def get_result():
    result = {
        "item_count": data.get_item_count(),
        "set_count": None,
        "status": data.get_status(),
    }

    return jsonify(result)


@bp.route("/debug")
def get_debug():
    items, _, _ = data.get_items(limit=10000)

    result = {
        "items": items,
        "suggestions": data.get_suggestions(),
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


@bp.route("/items")
def get_items():
    limit = int(request.args.get("limit", current_app.config.get("ITEMS_PER_PAGE")))
    after_ts = request.args.get("after_ts", type=int)
    after_id = request.args.get("after_id", type=int)
    order = request.args.get("order", "asc")

    items, next_after, has_more = data.get_items(
        limit=limit,
        after_ts=after_ts,
        after_id=after_id,
        order=order,
    )

    serialized_items = []
    for item in items:
        item = dict(item)
        item["id"] = str(item["id"])
        serialized_items.append(item)

    if next_after is not None:
        next_after = {
            "timestamp": next_after["timestamp"],
            "id": str(next_after["id"]),
        }

    return jsonify(
        {
            "items": serialized_items,
            "next_after": next_after,
            "has_more": has_more,
        }
    )


@bp.route("/set/<string:action>", methods=("POST",))
def move_set(action):
    logger = logging.getLogger("mediasort.api.move_set")

    payload = request.get_json(silent=True) or {}
    item_ids = payload.get("item_ids", [])
    try:
        item_ids = [int(item_id) for item_id in item_ids]
    except (TypeError, ValueError):
        return jsonify(data={"error": "Invalid item_ids"}), 400
    name = payload.get("name", "")

    if not item_ids:
        return jsonify(data={"error": "You must provide item_ids"}), 400

    if "save" in action and not name:
        return jsonify(data={"error": "You must provide a name to save"}), 400

    def actually_move(item_ids, name, testing=False):
        if testing:
            dry_run = True
        else:
            dry_run = current_app.config.get("DRY_RUN")

        if "save" in action:
            data.add_suggestion(name)

        data.move_items(action, item_ids, name=name, dry_run=dry_run)

    try:
        if current_app.testing:
            actually_move(item_ids, name, True)
        else:
            logger.info("Starting new thread for move")
            executor = Executor(current_app)
            executor.submit(actually_move, item_ids, name)
    except ValueError as exc:
        return jsonify(data={"error": str(exc)}), 400

    return jsonify(
        data={
            "result": "OK",
        }
    )


@bp.route("/suggestions")
def suggestions():
    return json.dumps(data.get_suggestions())
