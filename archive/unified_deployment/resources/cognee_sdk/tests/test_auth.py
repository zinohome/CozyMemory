"""
Unit tests for authentication API.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cognee_sdk import CogneeClient
from cognee_sdk.exceptions import ValidationError
from cognee_sdk.models import User


@pytest.fixture
def client():
    """Create a test client instance."""
    return CogneeClient(api_url="http://localhost:8000")


@pytest.mark.asyncio
async def test_login(client):
    """Test user login."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "test-token-123"}

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        token = await client.login("user@example.com", "password123")

        assert token == "test-token-123"
        assert client.api_token == "test-token-123"
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_login_validation_error(client):
    """Test login with empty credentials."""
    with pytest.raises(ValidationError):
        await client.login("", "password")

    with pytest.raises(ValidationError):
        await client.login("user@example.com", "")


@pytest.mark.asyncio
async def test_register(client):
    """Test user registration."""
    from uuid import uuid4

    user_id = uuid4()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": str(user_id),
        "email": "newuser@example.com",
        "created_at": "2025-01-01T00:00:00Z",
    }

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        user = await client.register("newuser@example.com", "password123")

        assert isinstance(user, User)
        assert user.email == "newuser@example.com"
        mock_request.assert_called_once()


@pytest.mark.asyncio
async def test_register_validation_error(client):
    """Test register with empty credentials."""
    with pytest.raises(ValidationError):
        await client.register("", "password")

    with pytest.raises(ValidationError):
        await client.register("user@example.com", "")


@pytest.mark.asyncio
async def test_get_current_user(client):
    """Test getting current user."""
    from uuid import uuid4

    user_id = uuid4()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": str(user_id),
        "email": "user@example.com",
    }

    with patch.object(client, "_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = mock_response
        user = await client.get_current_user()

        assert isinstance(user, User)
        assert user.email == "user@example.com"
        mock_request.assert_called_once()
