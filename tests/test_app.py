"""Tests for Flask application"""
import pytest


def test_app_creation(app):
    """Test that app is created successfully"""
    assert app is not None
    assert app.config["TESTING"] is True


def test_home_page(client):
    """Test home page loads"""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Nats RAG System" in response.data
    assert b"Search your indexed documents" in response.data


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "healthy"


def test_404_error(client):
    """Test 404 error handling"""
    response = client.get("/nonexistent-page")
    assert response.status_code == 404


def test_security_headers(client):
    """Test security headers are present"""
    response = client.get("/")
    assert "X-Content-Type-Options" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "Content-Security-Policy" in response.headers


def test_search_results_page(client):
    """Test search result page loads for a query"""
    response = client.get("/search-result?q=policy")
    assert response.status_code == 200
    assert b"Search Results" in response.data
