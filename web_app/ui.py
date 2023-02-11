from flask import (
    Blueprint,
    render_template,
    current_app,
    make_response,
)

from web_app import data, system

bp = Blueprint("ui", __name__, url_prefix="/")


@bp.route("/")
def index():

    num_items = current_app.config.get("SUMMARY_ITEMS")
    number_sets = current_app.config.get("SETS_SHOWN")
    base_path = current_app.config.get("INPUT_DIR")

    sets = data.get_top_tail_sets(num_sets=number_sets, max_items=2)

    # get_location is a function that is called
    return render_template(
        "index.html",
        sets=sets,
        limit=num_items,
        base_path=base_path,
        get_location=system.get_location,
    )


@bp.route("/set/<string:set_id>")
def full_set(set_id):

    base_path = current_app.config.get("INPUT_DIR")
    num_items = current_app.config.get("MAX_ITEMS")

    set = data.get_set(set_id, limit=num_items, store=True)

    # get_location is a function that is called
    return render_template(
        "set.html",
        set=set,
        base_path=base_path,
        get_location=system.get_location,
        no_more=True,
    )


@bp.route("/detach/<string:set_id>/<string:item_id>", methods=("POST",))
def detach(item_id, set_id):
    new_set = data.remove_item_from_set(item_id, set_id)

    return full_set(new_set.id)


@bp.route("/thumbnail/<string:item_id>.jpg")
@bp.route("/thumbnail/<int:size>/<string:item_id>.jpg")
def get_thumbnail(item_id, size=300):
    """Returns a wonderful thumbnail from the id"""

    path = data.get_item_path(item_id)

    # item = set.set[photo_id]
    thumbnail = system.make_thumbnail(path, size)

    response = make_response(thumbnail)
    response.content_type = "image/jpeg"
    return response
