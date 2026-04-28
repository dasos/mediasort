import logging
import threading
import time

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

    from . import db
    with app.app_context():
        db.init_db()
    app.teardown_appcontext(db.close_db)

    if not app.testing:
        _start_background_scanner(app)

    return app


def _start_background_scanner(app):
    interval_hours = app.config.get("SCAN_INTERVAL_HOURS")
    if not interval_hours:
        return

    interval_seconds = int(interval_hours * 3600)
    logger = logging.getLogger("mediasort")
    logger.info(f"Background scanner starting, interval={interval_hours}h")

    def loop():
        while True:
            time.sleep(interval_seconds)
            logger.info("Background scanner: checking for new files")
            with app.app_context():
                from web_app import data
                data.scan_new_files()

    threading.Thread(target=loop, daemon=True, name="mediasort-scanner").start()
