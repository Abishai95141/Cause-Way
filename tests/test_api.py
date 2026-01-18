"""Tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_endpoint_returns_200(self):
        """Test that health endpoint returns 200."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "ollama_available" in data
        assert "chromadb_available" in data
        assert "database_available" in data

    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "docs" in data


class TestAnalyzeEndpoint:
    """Test analyze endpoint."""

    def test_analyze_requires_question(self):
        """Test that analyze requires a question."""
        response = client.post("/api/analyze", json={})
        
        assert response.status_code == 422  # Validation error

    def test_analyze_accepts_valid_request(self):
        """Test that analyze accepts a valid request structure."""
        response = client.post(
            "/api/analyze",
            json={"question": "Should we reduce trial from 14 to 7 days?"}
        )
        
        # Will return 503 if Ollama not running, which is expected in test env
        # Just check it's not a validation error
        assert response.status_code != 422


# Note: Full integration tests require Ollama running
# Run with: pytest tests/test_api.py -v --ignore-glob="*integration*"
