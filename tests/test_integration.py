"""Integration tests for the newsletter manager system."""

import os

import pytest

from src.utils.config import Config


def test_config_loading():
    """Test that configuration loads successfully."""
    config = Config.from_env()

    # Check that essential config values are present
    assert config.gmail_credentials_path_1 is not None
    assert config.openai_api_key is not None
    assert config.database_url is not None


@pytest.mark.integration
def test_gmail_credentials_exist():
    """Test that Gmail credentials files exist."""
    config = Config.from_env()

    if config.gmail_credentials_path_1:
        assert os.path.exists(config.gmail_credentials_path_1)

    if config.gmail_credentials_path_2:
        assert os.path.exists(config.gmail_credentials_path_2)

    if config.gmail_credentials_path_3:
        assert os.path.exists(config.gmail_credentials_path_3)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gmail_connection():
    """Test Gmail connection without actually fetching emails."""
    pytest.skip("This test requires valid Gmail credentials and OAuth flow")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_outlook_connection():
    """Test Outlook connection without actually fetching emails."""
    pytest.skip("This test requires valid Outlook credentials and OAuth flow")


@pytest.mark.unit
def test_project_structure():
    """Test that essential project files exist."""
    essential_files = [
        "src/agents/base_agent.py",
        "src/services/gmail_service.py",
        "src/services/ai_service.py",
        "src/utils/config.py",
        "src/models/email.py",
        "main.py",
        "requirements.txt",
        "pyproject.toml",
    ]

    for file_path in essential_files:
        assert os.path.exists(file_path), f"Essential file missing: {file_path}"
