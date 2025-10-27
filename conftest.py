"""
Shared test fixtures and configuration for Envoxy tests.

This conftest.py file is automatically discovered by pytest and provides
fixtures that are available to all tests in the suite.
"""

import os
import sys
import pytest
from pathlib import Path

# Add src directory to path for imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


# Import fixtures from fixtures module
from tests.fixtures.fixtures import test_payload  # noqa: F401,F402,E402


@pytest.fixture(scope="session")
def project_root_dir():
    """Return the project root directory."""
    return project_root


@pytest.fixture(scope="session")
def test_data_dir(project_root_dir):
    """Return the test data directory."""
    return project_root_dir / "tests" / "data"


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture to set mock environment variables for testing."""
    test_vars = {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "test_db",
        "POSTGRES_USER": "test_user",
        "POSTGRES_PASSWORD": "test_password",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "COUCHDB_HOST": "localhost",
        "COUCHDB_PORT": "5984",
    }
    for key, value in test_vars.items():
        monkeypatch.setenv(key, value)
    return test_vars


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "server_key": "test_server",
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "test_db",
            "user": "test_user",
            "password": "test_password",
        },
        "redis": {
            "host": "localhost",
            "port": 6379,
        },
    }


# Test markers and skip conditions
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, isolated, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (database, external services)"
    )
    config.addinivalue_line(
        "markers", "slow: Slow-running tests"
    )
    config.addinivalue_line(
        "markers", "postgresql: Tests requiring PostgreSQL"
    )
    config.addinivalue_line(
        "markers", "redis: Tests requiring Redis"
    )
    config.addinivalue_line(
        "markers", "couchdb: Tests requiring CouchDB"
    )
    config.addinivalue_line(
        "markers", "mqtt: Tests requiring MQTT broker"
    )
    config.addinivalue_line(
        "markers", "celery: Tests requiring Celery worker"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Auto-mark based on path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Auto-mark based on test name
        if "postgresql" in item.nodeid.lower():
            item.add_marker(pytest.mark.postgresql)
        if "redis" in item.nodeid.lower():
            item.add_marker(pytest.mark.redis)
        if "couchdb" in item.nodeid.lower():
            item.add_marker(pytest.mark.couchdb)
        if "mqtt" in item.nodeid.lower():
            item.add_marker(pytest.mark.mqtt)


# Skip integration tests if running in CI without proper setup
@pytest.fixture(autouse=True)
def skip_integration_if_no_services(request):
    """Skip integration tests if external services are not available."""
    if request.node.get_closest_marker("integration"):
        # Check if we're in CI and skip if services aren't configured
        if os.getenv("CI") and not os.getenv("INTEGRATION_TESTS_ENABLED"):
            pytest.skip("Integration tests disabled in CI")
