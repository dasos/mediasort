import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify
)

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/status')
def get_result():

  from web_app.db import get_db

  redis_client = get_db()

  data = {
  	# TODO: make this more efficient
    'item_count': len(list(redis_client.scan_iter(match='item-*'))),
    'set_count': redis_client.zcount('set-start', '-inf', '+inf'),
    'status': redis_client.get('status')
  }

  return jsonify(data)

@bp.route('/reload')
def reload():

  from web_app import data

  data.populate_db()

  return jsonify(data = {
    'status': "OK",
  })
  