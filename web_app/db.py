from flask import current_app, g
from flask_redis import FlaskRedis

def get_db():

  if 'redis_client' in g:
    return g.redis_client

  if current_app.testing:
    import fakeredis
    #g.redis_client = fakeredis.FakeRedis()
    g.redis_client = FlaskRedis.from_custom_provider(fakeredis.FakeRedis, current_app, decode_responses=True)
  else:
    # For most Redis requests
    g.redis_client = FlaskRedis(current_app, decode_responses=True)

  return g.redis_client
