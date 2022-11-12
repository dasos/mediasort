import os
from flask import Flask

def create_app(config_map=None):
  """Create Flask app."""
  
  app = Flask(__name__)
  
  app.config.from_prefixed_env()
  
  # First try loading the defaults
  app.config.from_pyfile('../default_config.py')
  # Else, look for a environment variable called FLASK_
  app.config.from_prefixed_env()
  
  # Override anything being passed in specifically
  if config_map is not None:
    app.config.from_mapping(config_map)
    
  # Get url_for working behind SSL
  from werkzeug.middleware.proxy_fix import ProxyFix
  app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)


  from . import api, ui
  app.register_blueprint(api.bp)
  app.register_blueprint(ui.bp)

  return app