# CV Evaluator - Job Application Optimizer

A Flask rewrite of the job application optimizer with a glassmorphism UI, secure upload handling, and Heroku-friendly app factory pattern.

## Features

- 🤖 AI-powered CV evaluation using Groq LLM API
- 📄 Match your CV against job descriptions
- 🔒 Secure file upload handling
- 🎨 Modern glassmorphism UI design
- 📊 Real-time evaluation results
- 🚀 Production-ready with Heroku deployment
- 🛡️ Built-in security headers and CSRF protection
- 📉 Rate limiting per IP address

## Project Structure

```
nats_doc_rag_system/
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── config.py             # Configuration management
│   ├── extensions.py         # Flask extensions (CSRF)
│   ├── logging_utils.py      # JSON logging setup
│   ├── routes.py             # Route definitions
│   ├── templates/
│   │   └── index.html        # Home page template
│   └── static/               # Static files (CSS, JS, images)
├── tests/
│   ├── test_app.py          # App tests
│   └── test_routes.py       # Route tests
├── wsgi.py                   # WSGI entry point for deployment
├── Procfile                  # Heroku process file
├── runtime.txt              # Python version for Heroku
├── requirements.txt         # Python dependencies
├── settings_dev.py          # Development settings
├── settings_prod.py         # Production settings
├── pytest.ini               # Pytest configuration
├── .env.example             # Environment variables template
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Getting Started

### Prerequisites

- Python 3.12.9 or higher
- pip and virtualenv

### Local Development

1. **Clone and setup virtual environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   # or source .venv/bin/activate  # On macOS/Linux
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create `.env` file:**
   ```bash
   copy .env.example .env
   ```
   Edit `.env` with your values:
   ```
   FLASK_APP=wsgi.py
   FLASK_ENV=development
   FLASK_DEBUG=True
   FLASK_SECRET=your-secret-key-here
   GROQ_API_KEY=your-groq-api-key
   GROQ_MODEL=mixtral-8x7b-32768
   ```

4. **Run the application:**
   ```bash
   flask run
   ```
   The app will be available at http://localhost:5000

## Running Tests

```bash
pytest
```

To run with coverage:
```bash
pytest --cov=app tests/
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLASK_SECRET` | ✅ Yes | None | Flask secret key (generate with `python -c 'import secrets; print(secrets.token_hex(32))'`) |
| `GROQ_API_KEY` | ✅ Yes | None | API key from Groq console |
| `GROQ_MODEL` | ❌ No | `mixtral-8x7b-32768` | Groq model to use |
| `FLASK_DEBUG` | ❌ No | False | Enable debug mode |
| `FLASK_ENV` | ❌ No | development | Flask environment |

## Deploying to Heroku

1. **Create a Heroku app:**
   ```bash
   heroku create your-app-name
   ```

2. **Set environment variables:**
   ```bash
   heroku config:set FLASK_SECRET=$(python -c 'import secrets; print(secrets.token_hex(32))')
   heroku config:set GROQ_API_KEY=your-groq-api-key
   ```

3. **Deploy:**
   ```bash
   git push heroku main
   ```

4. **View logs:**
   ```bash
   heroku logs --tail
   ```

5. **Check health:**
   ```bash
   curl https://your-app-name.herokuapp.com/health
   ```

## Application Architecture

### Flask App Factory Pattern
The app uses the application factory pattern for better modularity and testability:
- `app/__init__.py`: Creates and configures the Flask app
- `app/config.py`: Configuration classes for different environments
- `app/extensions.py`: Flask extensions initialization
- `app/routes.py`: Route definitions

### Security Features
- **CSRF Protection**: Flask-WTF CSRF token validation
- **Security Headers**: X-Content-Type-Options, X-Frame-Options, Content-Security-Policy, etc.
- **Rate Limiting**: Per-IP rate limiting (100 requests per 60 seconds)
- **JSON Logging**: Structured logging for better observability

### Rate Limiting
The app implements per-IP rate limiting:
- **Window**: 60 seconds
- **Max Requests**: 100 per IP per window
- Returns 429 (Too Many Requests) when limit exceeded

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Home page with UI |
| `/health` | GET | Health check endpoint (returns JSON) |

## Development Workflow

1. Create a feature branch
2. Make changes and test locally
3. Run tests: `pytest`
4. Commit changes
5. Push to GitHub
6. Heroku auto-deploys from `main` branch (if connected)

## Troubleshooting

### "Too many requests" error
The app has rate limiting enabled. If you're getting 429 errors:
- Wait 60 seconds for the rate limit window to reset
- Or increase `RATE_LIMIT_MAX_REQUESTS` in `app/config.py`

### Missing environment variables
- Ensure `.env` file exists with all required variables
- Check: `FLASK_SECRET` and `GROQ_API_KEY` must be set

### Tests failing
- Make sure virtualenv is activated
- Run `pip install -r requirements.txt`
- Use `pytest -v` for verbose output

## Performance Notes

- **Gunicorn Workers**: Default is auto (2 × CPU + 1)
- **Dyno Type**: Works with Heroku's free and paid dynos
- **Memory**: ~512MB typical usage

## Related Links

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Groq API Docs](https://console.groq.com/docs)
- [Heroku Python Guide](https://devcenter.heroku.com/articles/python-support)
- [WSGI Standard](https://www.python.org/dev/peps/pep-3333/)

## License

MIT License - See LICENSE file for details

## Author

Nathaniel Cobbinah - [GitHub](https://github.com/natcobbinah)
