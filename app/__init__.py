from flask import Flask

from .app_env_config import Config
from .extensions import csrf
from .routes import main_bp


def create_app(config_object=None) -> Flask:
    app = Flask(__name__)

    app.config.from_object(config_object or Config)

    csrf.init_app(app)

    # register view blueprints
    _register_blueprints(app)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:;",
        )
        return response

    return app

def _register_blueprints(app):
    app.register_blueprint(main_bp)
