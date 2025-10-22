# Envoxy Quick Reference

A quick reference guide for common tasks in the reorganized Envoxy project.

## 🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/habitio/envoxy.git
cd envoxy
python3.12 -m venv venv
source venv/bin/activate
pip install -e .[dev]
pre-commit install

# Start development environment
cd docker/dev && docker-compose up -d
```

## 📦 Common Commands

### Build & Install

```bash
make install              # Install packages
make build                # Build packages
./tools/build.sh          # Alternative unified build
./tools/build.sh info     # Show build information
```

### Testing

```bash
make test                 # Run all tests
make test-unit            # Unit tests only
make test-integration     # Integration tests only
make test-cov             # Tests with coverage
make test-fast            # Skip slow tests
pytest -k test_name       # Run specific test
pytest -m postgresql      # Run tests with marker
```

### Code Quality

```bash
make lint                 # Run Ruff linter
make format               # Format code with Ruff
make type-check           # Run MyPy
make security-check       # Run Bandit
make quality-check        # Run all quality checks
make ci-local             # Full CI suite locally
```

### Pre-commit

```bash
pre-commit install        # Install hooks
pre-commit run --all-files # Run all hooks
make pre-commit-run       # Alternative
git commit                # Hooks run automatically
```

### Docker

```bash
# Development environment
cd docker/dev
docker-compose up -d      # Start all services
docker-compose down       # Stop all services
docker-compose logs -f    # View logs

# Build images
make docker-build         # Build all images
make docker-build-builder # Build builder images
make docker-build-runtime # Build runtime image

# Using build script
./tools/build.sh docker   # Build all Docker images
```

### Database Migrations

```bash
envoxy-alembic revision -m "description" --autogenerate
envoxy-alembic upgrade head
envoxy-alembic current
envoxy-alembic history
```

## 📁 Directory Structure

```
envoxy/
├── .github/workflows/    # CI/CD pipelines
├── docker/              # Docker configurations
│   ├── builder/        # Build environments
│   ├── runtime/        # Production images
│   └── dev/            # Development stack
├── docs/                # Documentation
├── src/envoxy/          # Main package source
├── tests/               # Test suite
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   └── fixtures/       # Test fixtures
├── tools/               # Build scripts
└── vendors/             # Third-party packages
```

## 🔧 Configuration Files

| File                            | Purpose                      |
| ------------------------------- | ---------------------------- |
| `pyproject.toml`                | Python project configuration |
| `pytest.ini`                    | Test configuration           |
| `.pre-commit-config.yaml`       | Pre-commit hooks             |
| `Makefile`                      | Build automation             |
| `docker/dev/docker-compose.yml` | Dev environment              |

## 📊 Test Markers

```bash
pytest -m unit            # Unit tests
pytest -m integration     # Integration tests
pytest -m slow            # Slow tests
pytest -m "not slow"      # Skip slow tests
pytest -m postgresql      # PostgreSQL tests
pytest -m redis           # Redis tests
pytest -m couchdb         # CouchDB tests
pytest -m mqtt            # MQTT tests
```

## 🐛 Debugging

```bash
# Run tests with verbose output
pytest -vv

# Stop on first failure
pytest -x

# Show print statements
pytest -s

# Debug mode
pytest --pdb

# Run last failed tests
pytest --lf
```

## 🔍 Code Search

```bash
# Find files
find src/ -name "*.py"

# Search code
grep -r "pattern" src/

# Find TODO items
grep -rn "TODO" src/
```

## 📈 Coverage

```bash
# Generate HTML coverage report
pytest --cov=src/envoxy --cov-report=html tests/

# View report
open htmlcov/index.html   # macOS
xdg-open htmlcov/index.html # Linux
```

## 🔒 Security

```bash
# Dependency vulnerabilities
safety check
pip-audit

# Code security
bandit -r src/envoxy/

# Secret scanning
detect-secrets scan
```

## 📝 Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes and test
make ci-local

# Commit (pre-commit hooks run automatically)
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/my-feature
```

## 🎯 Commit Message Format

```
<type>(<scope>): <subject>

Types: feat, fix, docs, style, refactor, test, chore
Examples:
  feat(cache): add Redis connection pooling
  fix(db): handle connection timeout
  docs: update installation guide
```

## 📦 Dependencies

```bash
# Install dev dependencies
pip install -e .[dev]

# Install test dependencies
pip install -e .[test]

# Install all
pip install -e .[dev,test]

# Update dependencies
pip install --upgrade -e .[dev,test]
```

## 🌐 Development Services

| Service      | URL                   | Credentials              |
| ------------ | --------------------- | ------------------------ |
| Envoxy       | http://localhost:8080 | -                        |
| PostgreSQL   | localhost:5432        | envoxy/envoxy            |
| pgAdmin      | http://localhost:5050 | admin@envoxy.local/admin |
| Redis        | localhost:6379        | -                        |
| RedisInsight | http://localhost:8001 | -                        |

## 📚 Documentation Links

- [README.md](../README.md) - Project overview
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guide
- [docs/BUILD.md](../docs/BUILD.md) - Build system
- [docs/CI-CD.md](../docs/CI-CD.md) - CI/CD pipelines
- [tests/README.md](../tests/README.md) - Testing guide
- [docker/README.md](../docker/README.md) - Docker guide
- [PROJECT-STATUS.md](../PROJECT-STATUS.md) - Project status

## 🆘 Troubleshooting

### Tests Failing

```bash
# Clear pytest cache
pytest --cache-clear

# Reinstall dependencies
pip install -e .[dev,test] --force-reinstall
```

### Docker Issues

```bash
# Rebuild images
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Clean Docker system
docker system prune -a
```

### Pre-commit Issues

```bash
# Update hooks
pre-commit autoupdate

# Reinstall
pre-commit uninstall
pre-commit install
```

## 💡 Pro Tips

1. **Use `make ci-local`** before pushing to catch issues early
2. **Run `./tools/build.sh info`** to verify environment
3. **Use test markers** to run specific test categories
4. **Check `make help`** for all available targets
5. **Read error messages** from pre-commit hooks - they're helpful!
6. **Use docker-compose** for consistent dev environment
7. **Keep dependencies updated** via Dependabot PRs

## 🔗 Quick Links

- **CI/CD**: [GitHub Actions](https://github.com/habitio/envoxy/actions)
- **Issues**: [GitHub Issues](https://github.com/habitio/envoxy/issues)
- **PRs**: [Pull Requests](https://github.com/habitio/envoxy/pulls)

---

**For detailed information, see the full documentation in the `docs/` directory.**
