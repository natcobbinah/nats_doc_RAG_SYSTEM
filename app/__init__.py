from flask import Flask
import os
from .app_env_config import Config
from .extensions import csrf
from .routes import main_bp
from .config import db
from .role_seed_script import seed_roles
from .utils.twilio_verification_sid import generate_twilio_verification_service_sid
from .models import RoleName
from .extensions import (
    login_manager,
    github,
    mail,
    oauth,
    flask_cache
)
from flask_migrate import Migrate
from flask_font_awesome import FontAwesome

font_awesome = FontAwesome()
migrate = Migrate()


def create_app(config_object=None) -> Flask:
    app = Flask(__name__)

    app.config.from_object(config_object or Config)

    # initialize csrf
    csrf.init_app(app)

    # initialize database
    db.init_app(app)

    # font awesome migration
    font_awesome.init_app(app)

    # database migration
    migrate.init_app(app, db)

    # set view function that handles logins 
    # so if any page requires authentication before access 
    # the application redirects the user to be authenticated here
    login_manager.login_view = 'auth_route.login'  # -----------------------to be corrected

    # override default flask-login message requiring users to login before 
    # accessing protected resources
    login_manager.login_message = ('Please log in to access this page.')

    # github oauth2
    github.init_app(app)

    #  authlib
    oauth.init_app(app)

    # oauthlib google initialization
    oauth.register(
        name='google',
        server_metadata_url=app.config["GOOGLE_OPENID_CONF_URL"],
        client_kwargs={
            'scope': 'openid email profile'
        },
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
    )

    oauth.register(
        name='twitter',
        client_id=app.config["TWITTER_OAUTH2_CLIENT_ID"],
        client_secret=app.config["TWITTER_OAUTH2_CLIENT_SECRET"],
        authorize_url=app.config["TWITTER_OAUTH2_CONF_URL"],
        access_token_url=app.config["TWITTER_OAUTH2_ACCESS_TOKEN_URL"],
        client_kwargs={
            "scope": "tweet.read users.read users.email offline.access",
            "code_challenge_method": "S256",
        }
    )

    # flask mail init
    mail.init_app(app)

    # flask caching
    flask_cache.init_app(app)

    # Make RoleName available inside Jinja templates
    app.jinja_env.globals["RoleName"] = RoleName

    # Allow getattr in templates
    app.jinja_env.globals["getattr"] = getattr

    # register view blueprints
    _register_blueprints(app)

    # create table schema in database
    _create_db_tables(app,db)

    # empty flask cache on application startup
    _empty_flask_cache_on_application_startup(app, flask_cache)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

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

def _empty_flask_cache_on_application_startup(app, flask_cache):
    with app.app_context():
        flask_cache.clear()

def _create_db_tables(app,db):
    with app.app_context():
        db.create_all()

        # if the roles already exist, the seed function will skip seeding and log that roles already exist
        seed_roles()

        # generate verification service sid and store in db if it doesn't already exist
        generate_twilio_verification_service_sid()
