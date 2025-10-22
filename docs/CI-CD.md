# CI/CD Pipeline Documentation

## Overview

Envoxy uses GitHub Actions for continuous integration and deployment with comprehensive automation for testing, security, quality checks, and publishing.

## Workflows

### 1. Test Suite (`.github/workflows/test.yml`)

**Triggers:**

- Push to: `main`, `develop`, `feature/*`
- Pull requests to: `main`, `develop`

**Jobs:**

- **Lint**: Ruff + Pylint code checks
- **Unit Tests**: Fast isolated tests (Python 3.12)
- **Integration Tests**: Tests with PostgreSQL + Redis services
- **All Tests**: Complete test suite with coverage

**Features:**

- ✅ Codecov integration for coverage tracking
- ✅ Artifacts: HTML coverage reports
- ✅ Matrix testing (future: multiple Python versions)

### 2. Security Scanning (`.github/workflows/security.yml`)

**Triggers:**

- Push to: `main`, `develop`
- Pull requests to: `main`, `develop`
- Schedule: Weekly on Mondays
- Manual: `workflow_dispatch`

**Jobs:**

- **Dependency Check**: Safety + pip-audit for vulnerable packages
- **Code Security**: Bandit for security issues in code
- **CodeQL**: GitHub's advanced security analysis
- **Trivy Scan**: Vulnerability scanning for dependencies and Docker images
- **Docker Security**: Scan Docker images for vulnerabilities
- **Secrets Scan**: Gitleaks for exposed secrets
- **Summary**: Aggregate security status

**Reports:**

- SARIF format uploaded to GitHub Security
- JSON reports as artifacts

### 3. Code Quality (`.github/workflows/quality.yml`)

**Triggers:**

- Push to: `main`, `develop`, `feature/*`
- Pull requests to: `main`, `develop`
- Manual: `workflow_dispatch`

**Jobs:**

- **Ruff**: Fast Python linter and formatter
- **Pylint**: Comprehensive code analysis (≥8.0 score)
- **MyPy**: Static type checking
- **Complexity**: Radon + Xenon for code complexity
- **Documentation**: pydocstyle + interrogate for docstring coverage
- **SonarCloud**: Advanced code quality and security (optional)

**Metrics:**

- Cyclomatic complexity
- Maintainability index
- Docstring coverage (≥50%)

### 4. Build and Publish (`.github/workflows/publish.yml`)

**Triggers:**

- Tags: `v*.*.*` (e.g., v0.5.0)
- Manual: `workflow_dispatch` with publish target selection

**Jobs:**

- **Build**: Create sdist and wheel for envoxy + envoxyd
- **Publish TestPyPI**: Publish to test.pypi.org (manual)
- **Publish PyPI**: Publish to pypi.org (on tags)
- **Docker Build**: Multi-arch (amd64/arm64) runtime + builder images

**Artifacts:**

- Python packages (wheels + sdist)
- Docker images (habitio/envoxy, habitio/envoxy-builder)
- GitHub Releases (automatic on tags)

## Pre-commit Hooks

Install locally: `pre-commit install`

**Hooks:**

- File checks (trailing whitespace, EOF, YAML/JSON/TOML)
- Ruff (linting + formatting)
- Bandit (security)
- MyPy (type checking)
- Markdown linting
- Shell script checking (shellcheck)
- Dockerfile linting (hadolint)
- Secrets detection

**CI Integration:**

- Runs on pre-commit.ci
- Auto-fixes and commits
- Weekly auto-updates

## Dependabot

**Configuration:** `.github/dependabot.yml`

**Monitored:**

- Python dependencies (pip)
- GitHub Actions
- Docker base images

**Schedule:** Weekly on Mondays
**Pull Requests:** Max 10 for Python, 5 for others

## Setup Requirements

### GitHub Secrets

Required secrets for full CI/CD:

```bash
# PyPI Publishing
PYPI_API_TOKEN              # For publishing to PyPI
TEST_PYPI_API_TOKEN         # For publishing to TestPyPI

# Docker Hub
DOCKERHUB_USERNAME          # Docker Hub username
DOCKERHUB_TOKEN             # Docker Hub access token

# Code Coverage
CODECOV_TOKEN               # Codecov.io upload token

# Code Quality (optional)
SONAR_TOKEN                 # SonarCloud token
GITLEAKS_LICENSE            # Gitleaks license (if using pro)
```

### Setting Secrets

```bash
# Using GitHub CLI
gh secret set PYPI_API_TOKEN
gh secret set TEST_PYPI_API_TOKEN
gh secret set DOCKERHUB_USERNAME
gh secret set DOCKERHUB_TOKEN
gh secret set CODECOV_TOKEN

# Or via GitHub UI:
# Settings → Secrets and variables → Actions → New repository secret
```

### Environments

Create GitHub Environments for deployment protection:

1. **testpypi**

   - URL: https://test.pypi.org/p/envoxy
   - Protection: Optional reviewers

2. **pypi**
   - URL: https://pypi.org/p/envoxy
   - Protection: Required reviewers
   - Deployment branches: Only `main` and tags

## Development Workflow

### Feature Development

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Pre-commit hooks run automatically

# Push to GitHub
git push origin feature/my-feature

# Create pull request
# CI runs: test, security, quality workflows
```

### Release Process

```bash
# 1. Update version in pyproject.toml
vim pyproject.toml  # Update version = "0.6.0"

# 2. Update CHANGELOG
vim CHANGELOG  # Add release notes

# 3. Commit version bump
git add pyproject.toml CHANGELOG
git commit -m "chore: bump version to 0.6.0"
git push

# 4. Create and push tag
git tag -a v0.6.0 -m "Release v0.6.0"
git push origin v0.6.0

# 5. CI automatically:
#    - Builds packages
#    - Publishes to PyPI
#    - Builds Docker images
#    - Creates GitHub Release
```

### Manual Publish

```bash
# Trigger manual workflow
gh workflow run publish.yml \
  --ref main \
  -f publish_to=testpypi  # or 'pypi' or 'none'
```

## Monitoring and Badges

### Status Badges

Add to README.md:

```markdown
[![Test Suite](https://github.com/habitio/envoxy/workflows/Test%20Suite/badge.svg)](https://github.com/habitio/envoxy/actions/workflows/test.yml)
[![Security](https://github.com/habitio/envoxy/workflows/Security%20Scanning/badge.svg)](https://github.com/habitio/envoxy/actions/workflows/security.yml)
[![Code Quality](https://github.com/habitio/envoxy/workflows/Code%20Quality/badge.svg)](https://github.com/habitio/envoxy/actions/workflows/quality.yml)
[![codecov](https://codecov.io/gh/habitio/envoxy/branch/main/graph/badge.svg)](https://codecov.io/gh/habitio/envoxy)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
```

### Coverage Tracking

Codecov provides:

- Coverage percentage
- Coverage diff in PRs
- Line-by-line coverage
- Trend graphs

Access: https://codecov.io/gh/habitio/envoxy

### Security Dashboard

GitHub Security:

- Dependabot alerts
- CodeQL findings
- Secret scanning
- Dependency graph

Access: Repository → Security tab

## Makefile Integration

```bash
# Pre-commit hooks
make pre-commit-install    # Install hooks
make pre-commit-run        # Run manually

# Testing
make test                  # Run all tests
make test-cov              # With coverage

# Quality checks
make lint                  # Run linters
make format                # Format code
make type-check            # MyPy type checking

# Security
make security-check        # Run security scans
make deps-check            # Check dependency vulnerabilities
```

## Local Development

### Install Pre-commit

```bash
pip install pre-commit
pre-commit install
```

### Run CI Checks Locally

```bash
# Install Act (run GitHub Actions locally)
brew install act  # macOS
# or: curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Run workflows locally
act push                   # Runs on push
act pull_request           # Runs on PR
act -j test-unit           # Run specific job
```

### Docker CI

```bash
# Test Docker builds locally
docker build -f docker/runtime/Dockerfile -t envoxy:test .
docker run --rm envoxy:test --version

# Test with docker-compose
cd docker/dev
docker-compose up --build
```

## Troubleshooting

### CI Failures

**Tests failing:**

```bash
# Run tests locally first
make test-unit
make test-integration  # Requires services

# Check test logs in GitHub Actions
gh run view <run-id>
```

**Build failures:**

```bash
# Test build locally
./tools/build.sh packages

# Check for missing dependencies
pip install -e .[dev,test]
```

**Security scan failures:**

```bash
# Run locally
pip install safety bandit
safety check
bandit -r src/
```

### Pre-commit Issues

```bash
# Update hooks
pre-commit autoupdate

# Run specific hook
pre-commit run ruff --all-files

# Skip hooks temporarily
git commit --no-verify
```

### Dependabot PRs

```bash
# Review and merge Dependabot PRs
gh pr list --author app/dependabot
gh pr view <pr-number>
gh pr merge <pr-number> --auto --squash
```

## Performance

### Workflow Optimization

- **Caching**: pip cache, Docker layers cached with GitHub Actions cache
- **Parallel Jobs**: Jobs run in parallel where possible
- **Matrix Strategy**: Can expand to multiple Python versions
- **Conditional Execution**: Skip jobs based on file changes

### Typical Run Times

- Test Suite: ~3-5 minutes
- Security Scan: ~2-3 minutes
- Code Quality: ~2-3 minutes
- Build & Publish: ~5-7 minutes

## Best Practices

1. **Always run tests locally** before pushing
2. **Keep workflows modular** for easier maintenance
3. **Use caching** to speed up CI
4. **Monitor security alerts** regularly
5. **Review Dependabot PRs** weekly
6. **Keep secrets secure** and rotate regularly
7. **Test release process** with TestPyPI first
8. **Document workflow changes** in this file

## Future Enhancements

- [ ] Add performance benchmarking workflow
- [ ] Set up automated documentation builds (Sphinx/MkDocs)
- [ ] Add E2E testing workflow
- [ ] Implement blue-green deployment
- [ ] Add Slack/Discord notifications
- [ ] Set up automatic changelog generation
- [ ] Add PR auto-labeling
- [ ] Implement canary releases

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Dependabot Configuration](https://docs.github.com/en/code-security/dependabot)
- [Pre-commit Hooks](https://pre-commit.com/)
- [Codecov Documentation](https://docs.codecov.io/)
- [PyPI Publishing](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
