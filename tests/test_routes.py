"""Tests for Flask application routes"""
import pytest


def test_index_route_returns_200(client):
    """Test index route returns 200 status"""
    response = client.get("/")
    assert response.status_code == 200


def test_index_contains_title(client):
    """Test index page contains landing page content"""
    response = client.get("/")
    assert b"Nats RAG System" in response.data
    assert b"Recent Documents" in response.data


def test_profile_redirects_when_not_authenticated(client):
    """Profile should require authentication"""
    response = client.get("/profile")
    assert response.status_code == 302
