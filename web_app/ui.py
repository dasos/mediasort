from flask import (
    Blueprint,
    render_template,
    current_app,
    make_response,
)

from web_app import data

bp = Blueprint("ui", __name__, url_prefix="/")


@bp.route("/")
def index():
    base_path = current_app.config.get("INPUT_DIR")

    return render_template(
        "index.html",
        base_path=base_path,
        gap_hours=current_app.config.get("SET_GAP_HOURS"),
        summary_items=current_app.config.get("SUMMARY_ITEMS"),
        sets_shown=current_app.config.get("SETS_SHOWN"),
        items_per_page=current_app.config.get("ITEMS_PER_PAGE"),
    )


@bp.route("/thumbnail/<string:item_id>")
@bp.route("/thumbnail/<int:size>/<string:item_id>")
@bp.route("/thumbnail/<string:type>/<string:item_id>")
def get_thumbnail(item_id, size=None, type=None):
    """Returns a wonderful thumbnail from the id"""

    if type == "detail":
        size = current_app.config.get("DETAIL_SIZE")
    elif type is not None or size is None:
        size = current_app.config.get("THUMBNAIL_SIZE")

    path = data.get_item_path(int(item_id))
    if path is None:
        response = make_response("", 404)
        return response

    from web_app import system

    thumbnail, content_type = system.make_thumbnail(path, size)

    response = make_response(thumbnail)
    response.content_type = content_type
    return response
