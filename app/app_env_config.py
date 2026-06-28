import os
try:
    from environs import Env
except ModuleNotFoundError:
    Env = None

if Env is not None:
    env = Env()
    env.read_env()


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get("FLASK_SECRET", "dev-secret-key-change-in-production")
    DEBUG = False
    TESTING = False
    WTF_CSRF_ENABLED = True
    
    # Rate limiting
    RATE_LIMIT_WINDOW_SECONDS = 60
    RATE_LIMIT_MAX_REQUESTS = 100
    
    # API Keys
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    GROQ_MODEL = os.environ.get("GROQ_MODEL", "mixtral-8x7b-32768")


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FLASK_ENV = "development"


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FLASK_ENV = "production"
    # In production, ensure SECRET_KEY is set
    SECRET_KEY = os.environ.get("FLASK_SECRET")
    if not SECRET_KEY and os.environ.get("FLASK_ENV") == "production":
        raise ValueError("FLASK_SECRET environment variable must be set in production")


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"


# Config selector
config_by_env = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}

# Get the config class based on environment
env_name = os.environ.get("FLASK_ENV", "development")
Config = config_by_env.get(env_name, DevelopmentConfig)
