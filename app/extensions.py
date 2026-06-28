from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from flask_github import GitHub
from flask_mail import Mail
from authlib.integrations.flask_client import OAuth
from flask_caching import Cache

csrf = CSRFProtect()
login_manager = LoginManager()
github = GitHub()
mail = Mail()
oauth = OAuth()
flask_cache = Cache(
    config = {
        "DEBUG": True,          # some Flask specific configs
        "CACHE_TYPE": "SimpleCache",  # Flask-Caching related configs
        "CACHE_DEFAULT_TIMEOUT": 300
    }
)