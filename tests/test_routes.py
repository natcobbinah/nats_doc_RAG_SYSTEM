"""Tests for Flask application routes"""
import pytest


def test_index_route_returns_200(client):
    """Test index route returns 200 status"""
    response = client.get("/")
    assert response.status_code == 200


def test_index_contains_title(client):
    """Test index page contains CV Evaluator title"""
    response = client.get("/")
    assert b"CV Evaluator" in response.data
    assert b"Job Application Optimizer" in response.data
