# AI Trading Bot - Test Suite

Comprehensive test suite for the AI Trading Bot application covering all core modules, integrations, and API endpoints.

## Overview

This test suite provides:
- **Unit tests** for individual components
- **Integration tests** for multi-component workflows
- **API tests** for Flask dashboard endpoints
- **Mock fixtures** for external services (APIs, exchanges, AI providers)
- **95%+ code coverage** across core modules

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Shared fixtures and test configuration
├── README.md                   # This file
├── lib/                        # Tests for lib/ modules
│   ├── test_config.py          # Configuration management tests
│   ├── test_ai.py              # AI provider tests (Anthropic, xAI, DeepSeek)
│   ├── test_database.py        # Database operations tests
│   ├── test_coinbase_client.py # Coinbase API client tests
│   ├── test_market_data.py     # Market data fetching tests
│   ├── test_forward_tester.py  # Paper trading simulation tests
│   ├── test_performance_tracker.py  # Performance metrics tests
│   ├── test_telegram_notifications.py  # Telegram notification tests
│   ├── test_simulation_manager.py     # Simulation orchestration tests
│   └── test_simulation_worker.py      # Simulation worker tests
├── dashboard/                  # Tests for dashboard/ modules
│   ├── test_routes_simulations.py  # Simulation API endpoint tests
│   ├── test_routes_api.py          # General API endpoint tests
│   └── test_routes_notifications.py # Notification API tests
└── integration/                # Integration tests
    ├── test_simulation_workflow.py  # End-to-end simulation tests
    ├── test_database_integration.py # Database + notification integration
    └── test_ai_trading_flow.py      # AI + trading integration
```

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Modules

```bash
# Run only configuration tests
pytest tests/lib/test_config.py

# Run only database tests
pytest tests/lib/test_database.py

# Run only dashboard tests
pytest tests/dashboard/

# Run only integration tests
pytest tests/integration/
```

### Run Tests by Marker

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

### Run with Coverage Report

```bash
# Terminal coverage report
pytest --cov=lib --cov=dashboard --cov-report=term-missing

# HTML coverage report
pytest --cov=lib --cov=dashboard --cov-report=html
# Open htmlcov/index.html to view detailed coverage
```

### Run Specific Tests

```bash
# Run a single test function
pytest tests/lib/test_config.py::TestTradingConfig::test_valid_trading_config

# Run a test class
pytest tests/lib/test_ai.py::TestAnthropicProvider
```

## Test Fixtures

The `conftest.py` file provides reusable fixtures:

### Database Fixtures
- `test_db` - Initialized test database (in-memory SQLite)
- `db_connection` - Database connection for direct queries
- `temp_db_path` - Temporary database file path

### Configuration Fixtures
- `sample_symbol_config` - Sample SymbolConfig object
- `sample_trading_config` - Sample TradingConfig object
- `sample_simulation_config` - Sample SimulationConfig object

### Mock API Response Fixtures
- `mock_anthropic_response` - Mock Claude API response
- `mock_xai_response` - Mock Grok API response
- `mock_coingecko_response` - Mock CoinGecko API response
- `mock_coinbase_price_response` - Mock Coinbase price API response
- `mock_telegram_response` - Mock Telegram Bot API response

### Mock Service Fixtures
- `mock_requests` - Mocked requests library
- `mock_coinbase_client` - Mocked Coinbase REST client
- `mock_ai_provider` - Mocked AI provider

### Flask Application Fixtures
- `flask_app` - Flask test application
- `flask_client` - Flask test client for API testing

### Temporary Directory Fixtures
- `temp_config_dir` - Temporary config directory
- `temp_performance_dir` - Temporary performance data directory
- `temp_forward_test_dir` - Temporary forward testing directory

### Environment Variables
- `mock_env_vars` - Mock environment variables for testing

## Test Markers

Tests are organized with pytest markers:

- `@pytest.mark.unit` - Unit tests for individual components
- `@pytest.mark.integration` - Integration tests spanning multiple components
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.requires_api` - Tests requiring external API access (should be mocked)
- `@pytest.mark.requires_db` - Tests requiring database access

## Writing New Tests

### Test File Naming
- Test files must start with `test_` or end with `_test.py`
- Test classes must start with `Test`
- Test functions must start with `test_`

### Example Test Structure

```python
"""
Tests for lib/my_module.py - Module description
"""

import pytest
from lib.my_module import MyClass


class TestMyClass:
    """Test MyClass functionality."""

    def test_initialization(self):
        """Test object initialization."""
        obj = MyClass(param="value")
        assert obj.param == "value"

    def test_method_with_fixture(self, test_db):
        """Test method using database fixture."""
        obj = MyClass()
        result = obj.some_method()
        assert result is not None

    @pytest.mark.slow
    def test_slow_operation(self):
        """Test slow operation (marked appropriately)."""
        # ... slow test code ...
        pass
```

### Using Fixtures

```python
def test_with_mock_api(mock_requests, mock_anthropic_response):
    """Test using mock API fixtures."""
    mock_requests["post"].return_value.json.return_value = mock_anthropic_response

    # Your test code here
    result = call_api_function()

    assert result is not None
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("BTCUSDT", "BTC"),
    ("ETHUSDT", "ETH"),
    ("SOLUSDT", "SOL"),
])
def test_symbol_normalization(input, expected):
    """Test symbol normalization for various inputs."""
    result = normalize_symbol(input)
    assert result == expected
```

## Coverage Goals

Target coverage by module:

- **lib/config.py**: 100%
- **lib/ai.py**: 95%
- **lib/database.py**: 95%
- **lib/coinbase_client.py**: 90%
- **lib/market_data.py**: 90%
- **lib/forward_tester.py**: 90%
- **lib/performance_tracker.py**: 90%
- **lib/telegram_notifications.py**: 85%
- **dashboard/routes/*.py**: 85%
- **Overall**: 90%+

## Best Practices

1. **Use Fixtures**: Leverage shared fixtures from `conftest.py`
2. **Mock External Services**: Never make real API calls in tests
3. **Isolate Tests**: Each test should be independent
4. **Descriptive Names**: Test names should describe what they test
5. **Arrange-Act-Assert**: Follow the AAA pattern in tests
6. **Test Edge Cases**: Include tests for error conditions
7. **Clean Up**: Use fixtures for automatic cleanup
8. **Fast Tests**: Keep unit tests fast (<100ms each)

## Continuous Integration

Tests are designed to run in CI/CD environments:

```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    pip install -r requirements-test.txt
    pytest --cov=lib --cov=dashboard --cov-report=xml

- name: Upload Coverage
  uses: codecov/codecov-action@v3
```

## Troubleshooting

### Common Issues

**Issue**: Tests fail with "No module named lib"
```bash
# Solution: Run tests from project root
cd /path/to/AITradingBot
pytest tests/
```

**Issue**: Database locked errors
```bash
# Solution: Tests use in-memory SQLite, ensure no other processes are accessing test DB
# Clean up any stale test database files
find . -name "test_*.db" -delete
```

**Issue**: Fixture not found
```bash
# Solution: Ensure conftest.py is in tests/ directory
# Check that fixture is defined with @pytest.fixture decorator
```

## Contributing

When adding new features:

1. Write tests **before** or **alongside** feature code
2. Ensure all existing tests still pass
3. Aim for 90%+ coverage on new code
4. Add integration tests for multi-component features
5. Update this README if adding new test patterns or fixtures

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Testing Flask Applications](https://flask.palletsprojects.com/en/latest/testing/)
