import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, jsonify
)

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/status')
def get_result():

  from web_app import system

  redis_client = system.get_db()

  result = {
  	# TODO: make this more efficient
    'item_count': len(list(redis_client.scan_iter(match='item-*'))),
    'set_count': redis_client.zcount('set-start', '-inf', '+inf'),
    'status': redis_client.get('status')
  }

  return jsonify(result)

@bp.route('/debug')
def get_debug():

  from web_app import system

  redis_client = system.get_db()
  
  
  items = []
  for name in redis_client.scan_iter(match='item-meta-*'):
    items.append({name: redis_client.hgetall(name)})

  sets = []
  for name in redis_client.scan_iter(match='set-meta-*'):
    set_id = redis_client.hget(name, 'id')
    sets.append(
      {'name': redis_client.hgetall(name),
       'items': [name for name in redis_client.zrange(f'set-items-{set_id}', 0, -1)],})

  result = {
    'items': items,
    'sets': sets,
  }

  return jsonify(result)


@bp.route('/reload')
def reload():

  from web_app import data

  data.clear_db()
  data.populate_db()

  return jsonify(data = {
    'status': "OK",
  })
  