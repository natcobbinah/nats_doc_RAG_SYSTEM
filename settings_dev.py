from environs import Env

env = Env()
env.read_env()

# Override in .env for local development
DEBUG = env.bool("FLASK_DEBUG", default=False)

# SECRET_KEY is required
SECRET_KEY = env.str("FLASK_SECRET", default="dev-secret-key-change-in-production")

# GROQ API KEY
GROQ_API_KEY = env.str("GROQ_API_KEY", default="")
GROQ_MODEL = env.str("GROQ_MODEL", default="mixtral-8x7b-32768")

# Rate limiting
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 100

GOOGLE_CLIENT_SECRET='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'
GOOGLE_CLIENT_ID = '641855247697-io9h4962rbmlc38uelfq8ud6v0fa92r6.apps.googleusercontent.com'

# WTForms
WTF_CSRF_ENABLED = True
