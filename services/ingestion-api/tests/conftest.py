"""Global test configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.auth import verify_api_key
from app.main import app


@pytest.fixture()
def client():
    """Test client fixture with API auth mocked."""

    # Override the API key dependency
    async def override_verify_api_key():
        return "test-api-key"

    app.dependency_overrides[verify_api_key] = override_verify_api_key
    client = TestClient(app)
    yield client
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture()
def authenticated_client():
    """Test client with real API key header."""
    return TestClient(app)
