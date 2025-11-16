import pytest
from fastapi.testclient import TestClient
from api.server import app, clerk_guard
from fastapi_clerk_auth import HTTPAuthorizationCredentials

class MockCredentials:
    """Mock credentials with decoded claims"""
    def __init__(self):
        self.scheme = "Bearer"
        self.credentials = "test-token"
        self.decoded = {"sub": "test-user-id"}

@pytest.fixture(scope="session")
def client():
    """Test client with mocked authentication"""
    
    # Override Clerk dependency to bypass auth
    app.dependency_overrides[clerk_guard] = lambda: MockCredentials()
    
    yield TestClient(app)
    
    # Cleanup
    app.dependency_overrides.clear()