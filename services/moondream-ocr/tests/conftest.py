"""Pytest configuration and shared fixtures for moondream-ocr tests."""

import sys
from pathlib import Path

import pytest

# Add the app directory to the Python path
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))


@pytest.fixture(scope="session")
def test_data_dir():
    """Directory containing test data files."""
    return Path(__file__).parent / "data"


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset global state before each test."""
    # Import after path is set
    import app.main

    # Reset the global OCR processor to None before each test
    app.main.ocr_processor = None

    yield

    # Clean up after test
    app.main.ocr_processor = None
