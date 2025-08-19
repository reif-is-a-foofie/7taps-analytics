# Tests Directory

This directory contains test files for the 7taps Analytics platform.

## Test Structure

- `test_*.py` - Individual test modules
- `test_csv_to_xapi.py` - CSV to xAPI conversion tests

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_file.py

# Run with coverage
pytest --cov=app tests/

# Run with verbose output
pytest -v
```

## Test Conventions

- Test files should be named `test_*.py`
- Test functions should be named `test_*`
- Use descriptive test names that explain what is being tested
- Include both unit tests and integration tests
- Mock external dependencies when appropriate

## Coverage

Maintain good test coverage for critical components:
- API endpoints
- ETL processes
- Data validation
- Database operations
