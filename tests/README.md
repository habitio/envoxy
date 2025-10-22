# Envoxy Test Suite

This directory contains the test suite for the Envoxy platform framework.

## Structure

```
tests/
├── conftest.py              # Shared fixtures and pytest configuration
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_asserts.py
│   ├── test_concurrency_pool.py
│   ├── test_envoxy_mixin.py
│   ├── test_postgresql_client.py
│   └── test_validate_models.py
├── integration/             # Integration tests (external services)
│   └── (future integration tests)
├── fixtures/                # Test fixtures and sample data
│   └── fixtures.py
└── data/                    # Test data files (future)
```

## Running Tests

### Install Test Dependencies

```bash
# Install with test dependencies
pip install -e .[test]

# Or install with dev dependencies (includes test)
pip install -e .[dev]
```

### Run All Tests

```bash
# Run all tests with coverage
pytest

# Run with verbose output
pytest -v

# Run in parallel (faster)
pytest -n auto
```

### Run Specific Test Categories

```bash
# Run only unit tests (fast)
pytest -m unit

# Run only integration tests
pytest -m integration

# Run tests requiring PostgreSQL
pytest -m postgresql

# Run tests requiring Redis
pytest -m redis

# Exclude slow tests
pytest -m "not slow"
```

### Run Specific Test Files

```bash
# Run a specific test file
pytest tests/unit/test_postgresql_client.py

# Run a specific test function
pytest tests/unit/test_postgresql_client.py::test_function_name

# Run tests matching a pattern
pytest -k "postgresql"
```

### Coverage Reports

```bash
# Run tests with coverage report
pytest --cov

# Generate HTML coverage report
pytest --cov --cov-report=html
# Then open htmlcov/index.html in browser

# Show missing lines
pytest --cov --cov-report=term-missing

# Set minimum coverage threshold
pytest --cov --cov-fail-under=80
```

## Test Markers

Tests are automatically marked based on their location and name:

- **`@pytest.mark.unit`** - Unit tests (auto-applied to tests in `unit/`)
- **`@pytest.mark.integration`** - Integration tests (auto-applied to tests in `integration/`)
- **`@pytest.mark.slow`** - Slow-running tests
- **`@pytest.mark.postgresql`** - Tests requiring PostgreSQL
- **`@pytest.mark.redis`** - Tests requiring Redis
- **`@pytest.mark.couchdb`** - Tests requiring CouchDB
- **`@pytest.mark.mqtt`** - Tests requiring MQTT broker
- **`@pytest.mark.celery`** - Tests requiring Celery worker

### Using Markers

```python
import pytest

@pytest.mark.unit
def test_fast_function():
    assert True

@pytest.mark.integration
@pytest.mark.postgresql
def test_database_connection():
    # Requires running PostgreSQL
    pass

@pytest.mark.slow
def test_long_running_operation():
    # Takes more than 1 second
    pass
```

## Fixtures

Shared fixtures are defined in `conftest.py`:

### Built-in Fixtures

- **`project_root_dir`** - Path to project root directory
- **`test_data_dir`** - Path to test data directory
- **`mock_env_vars`** - Mock environment variables (session scope)
- **`sample_config`** - Sample configuration dictionary
- **`test_payload`** - Sample test payload with various data types

### Using Fixtures

```python
def test_with_fixtures(test_payload, sample_config):
    """Test using shared fixtures."""
    assert "username" in test_payload
    assert sample_config["server_key"] == "test_server"
```

## Writing Tests

### Unit Test Example

```python
# tests/unit/test_mymodule.py
import pytest
from envoxy.mymodule import MyClass

@pytest.mark.unit
def test_my_function():
    """Test my function with clear description."""
    result = MyClass().my_method()
    assert result == expected_value
```

### Integration Test Example

```python
# tests/integration/test_database.py
import pytest
from envoxy import pgsqlc

@pytest.mark.integration
@pytest.mark.postgresql
def test_database_connection(sample_config):
    """Test real database connection."""
    # Requires running PostgreSQL instance
    result = pgsqlc.query("test_server", "SELECT 1")
    assert result is not None
```

### Using Mocks

```python
import pytest
from unittest.mock import Mock, patch

def test_with_mock(mocker):
    """Test using pytest-mock."""
    mock_func = mocker.patch('envoxy.module.function')
    mock_func.return_value = "mocked"

    result = call_function_that_uses_mock()
    assert result == "mocked"
    mock_func.assert_called_once()
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install -e .[test]

      - name: Run unit tests
        run: |
          pytest -m unit --cov --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
```

### Docker Compose for Integration Tests

```yaml
# docker-compose.test.yml
services:
  test:
    build: .
    command: pytest -m integration
    environment:
      POSTGRES_HOST: postgres
      REDIS_HOST: redis
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: test_db
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_password

  redis:
    image: redis:7-alpine
```

Run integration tests:

```bash
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## Best Practices

### 1. Test Isolation

Each test should be independent and not rely on other tests:

```python
# ✅ Good - isolated test
def test_user_creation():
    user = create_user("test@example.com")
    assert user.email == "test@example.com"
    cleanup_user(user)

# ❌ Bad - depends on previous test
def test_user_login():
    # Assumes user from previous test exists
    user = get_user("test@example.com")
    assert user.login()
```

### 2. Use Descriptive Names

```python
# ✅ Good - clear what's being tested
def test_user_cannot_login_with_wrong_password():
    pass

# ❌ Bad - unclear purpose
def test_login():
    pass
```

### 3. Arrange-Act-Assert Pattern

```python
def test_user_age_validation():
    # Arrange - setup test data
    user_data = {"name": "John", "age": 17}

    # Act - perform action
    result = validate_user(user_data)

    # Assert - verify outcome
    assert result.is_valid is False
    assert "age" in result.errors
```

### 4. Test Edge Cases

```python
@pytest.mark.parametrize("age", [0, -1, 150, None])
def test_invalid_ages(age):
    """Test edge cases for age validation."""
    assert not is_valid_age(age)
```

### 5. Keep Tests Fast

- Use mocks for external dependencies in unit tests
- Mark slow tests with `@pytest.mark.slow`
- Run integration tests separately from unit tests

## Troubleshooting

### Tests Not Found

```bash
# Check test discovery
pytest --collect-only

# Ensure test files start with test_
# Ensure test functions start with test_
```

### Import Errors

```bash
# Ensure package is installed in development mode
pip install -e .

# Or add src to PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
```

### Database Connection Errors

```bash
# Start services with docker-compose
cd docker/dev
docker-compose up -d postgres redis

# Check connection
docker-compose exec postgres psql -U envoxy -d envoxy -c "SELECT 1"
```

### Coverage Not Working

```bash
# Ensure pytest-cov is installed
pip install pytest-cov

# Run with explicit source
pytest --cov=src/envoxy --cov-report=term
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [pytest-mock Documentation](https://pytest-mock.readthedocs.io/)

## Contributing

When adding new tests:

1. Place unit tests in `tests/unit/`
2. Place integration tests in `tests/integration/`
3. Add appropriate markers
4. Update this README if adding new test categories
5. Ensure all tests pass before committing:
   ```bash
   pytest -m unit  # Fast unit tests
   pytest          # All tests
   ```
