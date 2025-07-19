import pytest
from fastapi.testclient import TestClient

from nova_manager.main import app

@pytest.fixture(scope="module")
def client():
    """TestClient fixture for integration tests."""
    return TestClient(app)
