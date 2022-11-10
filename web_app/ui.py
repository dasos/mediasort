import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify, current_app
)

bp = Blueprint('ui', __name__, url_prefix='/')

from web_app import data


@bp.route('/')
def index():

  num_thumbnails = current_app.config.get('THUMBNAILS')
  number_sets = current_app.config.get('SETS_SHOWN')
  base_path = current_app.config.get('INPUT_DIR')  


  sets = data.get_sets()


  return render_template('index.html', sets=sets, num_thumbnails=num_thumbnails, base_path=base_path)
  