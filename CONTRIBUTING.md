# Contributing to Envoxy

Thank you for your interest in contributing to Envoxy! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Code Style](#code-style)
- [Building Docker Images](#building-docker-images)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)

## Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/habitio/envoxy.git
cd envoxy
```

### 2. Create a Virtual Environment

```bash
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

Install the package in development mode with all dependencies:

```bash
# Install with dev dependencies
pip install -e .[dev]

# Or install everything (dev + test dependencies)
pip install -e .[dev,test]
```

### 4. Install Pre-commit Hooks

Pre-commit hooks will automatically run checks before each commit:

```bash
pre-commit install
```

To run all hooks manually:

```bash
make pre-commit-run
# or
pre-commit run --all-files
```

## Project Structure

```
envoxy/
├── src/envoxy/           # Main package source
│   ├── auth/            # Authentication backends
│   ├── cache/           # Redis cache utilities
│   ├── couchdb/         # CouchDB client
│   ├── db/              # Database utilities and ORM
│   │   └── orm/        # SQLAlchemy ORM extensions
│   ├── http/            # HTTP dispatcher
│   ├── mqtt/            # MQTT dispatcher
│   ├── postgresql/      # PostgreSQL client
│   ├── redis/           # Redis client
│   ├── tests/           # Package-level tests
│   ├── tools/           # CLI tools (alembic, validation)
│   ├── utils/           # Utility functions
│   ├── views/           # View helpers
│   └── zeromq/          # ZeroMQ integration
├── tests/               # Test suite
│   └── unit/           # Unit tests
├── vendors/             # envoxyd package (uWSGI integration)
├── docker/              # Docker configurations
│   ├── dev/            # Local development environment
│   └── runtime/        # Runtime Dockerfile
├── .github/             # GitHub Actions workflows
│   └── workflows/      # CI/CD pipelines
├── docs/                # Documentation
├── scripts/             # Utility scripts
└── pyproject.toml       # Package metadata and dependencies
```

## Running Tests

### Run All Tests

```bash
make test
# or
pytest tests/
```

### Run Specific Test Categories

```bash
# Unit tests only
make test-unit
# or
pytest tests/unit/

# Integration tests only
make test-integration
# or
pytest tests/integration/

# Fast tests (skip slow tests)
make test-fast
# or
pytest -m "not slow"
```

### Run Tests with Coverage

```bash
make test-cov
# or
pytest --cov=src/envoxy --cov-report=html tests/
```

View coverage report:

```bash
open htmlcov/index.html  # On macOS
xdg-open htmlcov/index.html  # On Linux
```

### Run Specific Tests

```bash
# By file
pytest tests/unit/test_decorators.py

# By test name
pytest tests/unit/test_decorators.py::test_auto_reconnect

# By marker
pytest -m postgresql  # Run only PostgreSQL tests
pytest -m "not slow"  # Skip slow tests
```

## Code Style

We maintain high code quality standards using multiple tools:

### Linting and Formatting

**Ruff** is our primary linter and formatter:

```bash
# Check for issues
make lint
# or
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/

# Format code
make format
# or
ruff format src/ tests/
```

### Type Checking

**MyPy** ensures type safety:

```bash
make type-check
# or
mypy src/envoxy/
```

### Additional Checks

**Pylint** provides additional code quality checks:

```bash
pylint src/envoxy/
```

**Bandit** scans for security issues:

```bash
bandit -r src/envoxy/
```

### Run All Quality Checks Locally

```bash
# Run the full CI suite locally
make ci-local
```

This will run:

- Linting (Ruff)
- Formatting checks (Ruff)
- Type checking (MyPy)
- Security scanning (Bandit)
- Tests (pytest)

## Building and Local Development

### Local Development with Docker

For local development and testing, use the Docker development environment:

```bash
cd docker/dev

# Start all services (postgres, redis, envoxy runtime)
docker compose up -d

# View logs
docker compose logs -f envoxy

# Stop services
docker compose down
```

See [docker/dev/README.md](docker/dev/README.md) for detailed instructions.

### Building Packages

**Package building and publishing is handled by GitHub Actions.** The CI/CD workflows automatically:

- Build envoxy and envoxyd packages
- Run all tests and quality checks
- Publish to PyPI on tagged releases

See `.github/workflows/` for the automation:

- `envoxy-publish.yml` - Builds and publishes envoxy to PyPI
- `envoxyd-manylinux.yml` - Builds manylinux wheels for envoxyd

To test package builds locally:

```bash
# Build envoxy
python -m build

# Build envoxyd
cd vendors
python -m build
```

## Submitting Changes

### 1. Create a Feature Branch

```bash
git checkout -b feature/my-new-feature
# or
git checkout -b fix/bug-description
```

Branch naming conventions:

- `feature/` - New features
- `fix/` - Bug fixes
- `refactor/` - Code refactoring
- `docs/` - Documentation changes
- `test/` - Test additions/modifications

### 2. Make Your Changes

- Write clean, maintainable code
- Follow existing code style and patterns
- Add docstrings to functions and classes
- Keep changes focused and atomic

### 3. Add Tests

- Add unit tests for new functionality
- Add integration tests if needed
- Ensure all tests pass: `make test`
- Maintain or improve code coverage

### 4. Run Quality Checks

Before committing, ensure all checks pass:

```bash
# Pre-commit hooks will run automatically on commit
git add .
git commit -m "feat: add new feature"

# Or run checks manually
make ci-local
```

### 5. Write Good Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions/modifications
- `chore`: Build process or auxiliary tool changes

Examples:

```bash
git commit -m "feat(cache): add Redis connection pooling"
git commit -m "fix(db): handle connection timeout properly"
git commit -m "docs: update installation instructions"
```

### 6. Push and Create Pull Request

```bash
git push origin feature/my-new-feature
```

Then create a Pull Request on GitHub with:

- Clear description of changes
- Reference to related issues
- Screenshots (if UI changes)
- Test results (if applicable)

### Pull Request Checklist

Before submitting, ensure:

- [ ] Code follows project style guidelines
- [ ] Tests pass locally (`make test`)
- [ ] New tests added for new functionality
- [ ] Documentation updated (if needed)
- [ ] Commit messages follow conventions
- [ ] No merge conflicts with main branch
- [ ] Pre-commit hooks pass

## Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality (backwards-compatible)
- **PATCH**: Bug fixes (backwards-compatible)

## Release Process

Releases are automated via GitHub Actions:

1. **Update version numbers** using the version bump script:

   ```bash
   # Bump patch version for both packages
   ./scripts/version_bump.sh patch

   # Or specify which package(s) to bump
   ./scripts/version_bump.sh patch envoxy    # Only envoxy
   ./scripts/version_bump.sh minor envoxyd   # Only envoxyd
   ```

2. **Commit and push** the version changes:

   ```bash
   git add pyproject.toml vendors/pyproject.toml src/envoxy/__init__.py
   git commit -m "chore: bump version to X.Y.Z"
   git push origin feature/your-branch
   ```

3. **Create a pull request** and merge to main after review

4. **Tag the release** after merging to main:

   ```bash
   git checkout main
   git pull
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin vX.Y.Z
   ```

5. **GitHub Actions automatically**:
   - Builds envoxy and envoxyd packages
   - Runs all tests and quality checks
   - Publishes to PyPI
   - Creates GitHub release

See `.github/workflows/` for the automation details.

## Getting Help

- **Documentation**: See [docs/](docs/) directory
- **Issues**: [GitHub Issues](https://github.com/habitio/envoxy/issues)
- **Discussions**: [GitHub Discussions](https://github.com/habitio/envoxy/discussions)

## Code of Conduct

Please be respectful and constructive in all interactions. We aim to maintain a welcoming and inclusive community.

## License

By contributing to Envoxy, you agree that your contributions will be licensed under the same license as the project (see [LICENSE](LICENSE)).

---

Thank you for contributing to Envoxy! 🚀
