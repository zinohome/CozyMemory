# Contributing to Cognee Python SDK

Thank you for your interest in contributing to Cognee Python SDK! This document provides guidelines and instructions for contributing.

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-org/cognee-sdk.git
   cd cognee-sdk
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run tests**
   ```bash
   pytest
   ```

## Code Style

We follow PEP 8 and use the following tools:

- **ruff** - Code formatting and linting
- **mypy** - Type checking
- **black** - Code formatting (via ruff)

### Before Committing

```bash
# Format code
ruff format .

# Check code
ruff check .

# Type check
mypy cognee_sdk/

# Run tests
pytest
```

## Development Guidelines

### Type Hints

- All functions must have complete type hints
- Use `Optional[T]` for optional parameters
- Use `Union[T1, T2]` for union types

### Docstrings

- All public classes and methods must have docstrings
- Use Google or NumPy style
- Include Args, Returns, Raises, and Examples sections

### Testing

- Write tests for all new features
- Aim for ≥80% test coverage
- Use `pytest` and `pytest-asyncio` for async tests
- Mock HTTP requests in unit tests

### Error Handling

- Use appropriate exception types from `exceptions.py`
- Provide clear error messages
- Include context in error information

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Add tests for new functionality
4. Update documentation as needed
5. Ensure all tests pass
6. Run code quality checks
7. Submit a pull request with a clear description

## Code Review

- All code must be reviewed before merging
- Address review comments promptly
- Keep pull requests focused and small when possible

## Questions?

Feel free to open an issue for questions or discussions.

