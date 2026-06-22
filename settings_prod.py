from environs import Env

env = Env()
env.read_env()

# Override in .env for local development
DEBUG = env.bool("FLASK_DEBUG", default=False)

# SECRET_KEY is required
SECRET_KEY = env.str("FLASK_SECRET")

# GROQ API KEY
GROQ_API_KEY = env.str("GROQ_API_KEY")
GROQ_MODEL = env.str("GROQ_MODEL", default="mixtral-8x7b-32768")

# Rate limiting
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 100

# WTForms
WTF_CSRF_ENABLED = True
