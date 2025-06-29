# Testing Documentation

## Overview

Loom v2 uses a comprehensive testing strategy with pytest for unit and integration testing. The test suite covers individual components, API endpoints, WebSocket functionality, and end-to-end workflows.

## Running Tests

### Essential Commands

```bash
# Run all tests (71 total)
make test

# Run tests with coverage report
make test-coverage

# Run only integration tests
make test-integration

# Run a specific test file
pytest services/ingestion-api/tests/unit/test_health.py -v

# Run tests matching a pattern
pytest -k "test_websocket" -v

# Run tests in watch mode (development)
cd services/ingestion-api && make test-watch
```

### Service-Specific Testing

Each service has its own test commands:

```bash
# Ingestion API
cd services/ingestion-api
make test              # Run unit tests
make test-coverage     # Generate coverage report
make test-integration  # Run integration tests
make test-watch        # Run tests in watch mode

# Email Fetcher
cd services/email-fetcher
make test

# Calendar Fetcher
cd services/calendar-fetcher
make test

# Pipeline Monitor API
cd services/pipeline-monitor-api
npm test
```

## Test Structure

### Ingestion API Test Organization

```
services/ingestion-api/tests/
├── unit/                    # Unit tests for individual components
│   ├── test_lifespan.py     # Application startup/shutdown
│   ├── test_health.py       # Health endpoints (/healthz, /readyz)
│   ├── test_metrics.py      # Prometheus metrics collection
│   ├── test_cors.py         # CORS configuration
│   ├── test_exceptions.py   # Error handling and responses
│   └── test_websocket.py    # WebSocket functionality
├── integration/             # End-to-end integration tests
└── conftest.py              # Shared test fixtures and configuration
```

## Test File Descriptions

### Unit Tests

#### test_lifespan.py
- Tests application startup and shutdown sequences
- Verifies Kafka producer initialization
- Ensures proper resource cleanup on shutdown
- Tests error handling during startup failures

#### test_health.py
- Tests `/healthz` liveness probe endpoint
- Tests `/readyz` readiness probe endpoint
- Verifies health check responses and status codes
- Tests dependency health checking (Kafka, database)

#### test_metrics.py
- Tests Prometheus metrics endpoint (`/metrics`)
- Verifies metric collection and formatting
- Tests custom application metrics
- Validates metric naming conventions

#### test_cors.py
- Tests CORS (Cross-Origin Resource Sharing) configuration
- Verifies allowed origins, methods, and headers
- Tests preflight requests
- Validates CORS headers in responses

#### test_exceptions.py
- Tests global exception handling
- Verifies error response formatting
- Tests validation error handling
- Ensures proper logging of exceptions

#### test_websocket.py
- Tests WebSocket connection establishment
- Verifies real-time data streaming
- Tests connection lifecycle management
- Validates WebSocket error handling

### Integration Tests

Integration tests verify end-to-end workflows:
- Device registration and management
- Audio upload and streaming
- Sensor data ingestion
- Kafka message publishing
- Database interactions

## Test Configuration

### conftest.py
The shared test configuration file provides:
- Test fixtures for FastAPI test client
- Mock Kafka producer
- Database test fixtures
- WebSocket test utilities
- Environment variable overrides

### Test Environment Variables
```python
# Override settings for testing
os.environ["LOOM_ENVIRONMENT"] = "testing"
os.environ["LOOM_DATABASE_URL"] = "postgresql://test:test@localhost:5432/test"
os.environ["LOOM_KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"
```

## Writing Tests

### Test Naming Conventions
- Test files: `test_<module>.py`
- Test functions: `test_<functionality>_<scenario>`
- Test classes: `Test<Component>`

### Example Unit Test
```python
import pytest
from fastapi.testclient import TestClient

def test_health_endpoint_returns_ok(client: TestClient):
    """Test that health endpoint returns 200 OK."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

### Example Integration Test
```python
import pytest
from fastapi.testclient import TestClient

def test_device_registration_workflow(client: TestClient):
    """Test complete device registration workflow."""
    # Register device
    device_data = {
        "device_id": "test-device-001",
        "device_type": "android",
        "metadata": {"model": "Pixel 8"}
    }
    response = client.post("/devices", json=device_data)
    assert response.status_code == 201

    # Verify device exists
    response = client.get(f"/devices/{device_data['device_id']}")
    assert response.status_code == 200
    assert response.json()["device_id"] == device_data["device_id"]
```

## Test Coverage

### Viewing Coverage Reports
```bash
# Generate HTML coverage report
make test-coverage

# View coverage in terminal
pytest --cov=app --cov-report=term-missing

# Generate XML report for CI
pytest --cov=app --cov-report=xml
```

### Coverage Goals
- Unit test coverage: >80%
- Critical path coverage: 100%
- Integration test coverage: Key workflows

## CI/CD Testing

### GitHub Actions Workflow
Tests run automatically on:
- Pull request creation/update
- Commits to main branch
- Scheduled nightly runs

### CI Test Pipeline
1. **Linting**: Code style and quality checks
2. **Type Checking**: mypy static analysis
3. **Unit Tests**: Fast, isolated component tests
4. **Integration Tests**: End-to-end workflow tests
5. **Security Scans**: Dependency and code scanning

## Testing Best Practices

### General Guidelines
1. **Test Independence**: Tests should not depend on each other
2. **Fast Execution**: Unit tests should complete in <1 second
3. **Clear Naming**: Test names should describe what they verify
4. **Arrange-Act-Assert**: Structure tests with clear sections
5. **Mock External Dependencies**: Use mocks for Kafka, databases, etc.

### FastAPI Testing Tips
- Use `TestClient` for synchronous endpoint testing
- Use `httpx.AsyncClient` for async endpoint testing
- Test both success and error paths
- Verify response status codes and content
- Test request validation

### WebSocket Testing
- Test connection establishment and teardown
- Verify message sending and receiving
- Test error handling and reconnection
- Use async test functions with `pytest-asyncio`

## Debugging Tests

### Running Tests with Debugging
```bash
# Run with verbose output
pytest -vv

# Run with print statements visible
pytest -s

# Run with pdb debugger on failure
pytest --pdb

# Run specific test with debugging
pytest -vvs -k "test_specific_function" --pdb
```

### Common Test Issues

#### Import Errors
- Ensure PYTHONPATH includes project root
- Check for circular imports
- Verify __init__.py files exist

#### Fixture Errors
- Check fixture scope (function, module, session)
- Verify fixture dependencies
- Look for fixture name conflicts

#### Async Test Issues
- Use `pytest.mark.asyncio` decorator
- Install `pytest-asyncio`
- Properly await async operations

## Performance Testing

### Load Testing with Locust
```python
# locustfile.py
from locust import HttpUser, task, between

class LoomUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def upload_audio(self):
        self.client.post("/audio/upload", json={
            "device_id": "test-device",
            "audio_data": "base64_encoded_audio",
            "metadata": {"sample_rate": 16000}
        })
```

Run load tests:
```bash
locust -f locustfile.py --host=http://localhost:8000
```

## Test Data Management

### Fixtures for Test Data
```python
# conftest.py
@pytest.fixture
def sample_audio_data():
    """Provide sample audio data for testing."""
    return {
        "device_id": "test-device-001",
        "audio_data": base64.b64encode(b"fake_audio_data").decode(),
        "metadata": {
            "sample_rate": 16000,
            "channels": 1,
            "duration_ms": 1000
        }
    }
```

### Test Database
- Use separate test database
- Reset between test runs
- Use transactions for isolation
- Consider using factories for complex data

## Monitoring Test Health

### Test Metrics to Track
- Test execution time trends
- Flaky test frequency
- Coverage changes over time
- Test failure patterns

### Maintaining Test Suite
- Regular test review and cleanup
- Update tests when features change
- Remove obsolete tests
- Refactor duplicate test logic
