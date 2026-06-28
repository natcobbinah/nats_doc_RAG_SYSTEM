"""Pytest configuration and fixtures"""
import sys
from pathlib import Path

# Add the parent directory to the path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from app import create_app
from app.app_env_config import TestingConfig


@pytest.fixture
def app():
    """Create and configure a test app"""
    app = create_app(TestingConfig)
    
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """A test client for the app"""
    return app.test_client()
