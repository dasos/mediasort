import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify, current_app, make_response
)

bp = Blueprint('ui', __name__, url_prefix='/')

from web_app import data, system


@bp.route('/')
def index():

  num_thumbnails = current_app.config.get('THUMBNAILS')
  number_sets = current_app.config.get('SETS_SHOWN')
  base_path = current_app.config.get('INPUT_DIR')  

  sets = data.get_sets()

  return render_template('index.html', sets=sets, num_thumbnails=num_thumbnails, base_path=base_path)


@bp.route('/thumbnail/<int:item_id>.jpg')
@bp.route('/thumbnail/<int:size>/<int:item_id>.jpg')
def get_thumbnail(item_id, size=300):
  '''Returns a wonderful thumbnail from the id'''

  redis_client = system.get_db()

  path = data.get_item_path(item_id)
  
  #item = set.set[photo_id]
  thumbnail = system.make_thumbnail(path, size)

  response = make_response(thumbnail)
  response.content_type = 'image/jpeg'
  return response
