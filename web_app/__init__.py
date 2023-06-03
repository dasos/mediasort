import logging
from flask import Flask


def create_app(config_map=None):
    """Create Flask app."""

    app = Flask(__name__)

    # First, pull in the environment variables called FLASK_*. This will let
    # us know if we are in a dev environment
    app.config.from_prefixed_env()

    # Always get the defaults
    app.config.from_pyfile("../default_config.py")

    # Overwrite with others if needed
    if app.config.get("DEBUG"):
        app.config.from_pyfile("../default_config_dev.py")

    # Pull in the env variables again, to overwrite anything here
    app.config.from_prefixed_env()
    
    print (app.config.get("INPUT_DIR"))

    # Override anything being passed in specifically
    if config_map is not None:
        app.config.from_mapping(config_map)

    # Get url_for working behind SSL
    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)

    # Set up some logging defaults based upon the config. Keep the basic config at warn, so our libraries don't overwhelm us
    logging.basicConfig(level="WARN")
    logging.getLogger("mediasort").setLevel(app.config.get("DEBUG_LEVEL"))

    # logging.getLogger("PIL").setLevel("WARN")

    from . import api, ui

    app.register_blueprint(api.bp)
    app.register_blueprint(ui.bp)

    return app
