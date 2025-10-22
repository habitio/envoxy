# Requirements Management

## Generate requirements.txt from pyproject.toml

This project uses `pyproject.toml` as the single source of truth for dependencies. Use `pip-compile` to generate pinned `requirements.txt`.

### Quick start

```bash
# Generate requirements.txt from pyproject.toml
./tools/generate-requirements.sh

# Upgrade all dependencies to latest compatible versions
./tools/generate-requirements.sh --upgrade

# Generate dev requirements too
./tools/generate-requirements.sh --dev

# Upgrade and include dev dependencies
./tools/generate-requirements.sh --upgrade --dev
```

### Manual usage

If you prefer to run pip-compile directly:

```bash
# Install pip-tools
pip install pip-tools

# Generate from pyproject.toml (recommended)
pip-compile --output-file=requirements.txt pyproject.toml

# Generate with upgrades
pip-compile --upgrade --output-file=requirements.txt pyproject.toml

# Generate dev requirements
pip-compile --extra=dev --output-file=requirements-dev.txt pyproject.toml

# Generate vendor requirements (envoxyd)
cd vendors
pip-compile --output-file=requirements.txt ../pyproject.toml
```

### Workflow

1. **Edit dependencies** in `pyproject.toml` (either `[project]` or `[tool.vendors.envoxyd]`)
2. **Run** `./tools/generate-requirements.sh` to create pinned `requirements.txt`
3. **Commit** both `pyproject.toml` and `requirements.txt`
4. **In CI/Docker**: use `requirements.txt` for reproducible builds

### Why pip-compile?

-   **Pinned versions**: Generates exact versions for reproducible builds
-   **Dependency tree**: Shows why each package is installed
-   **Upgrade safety**: `--upgrade` only updates to compatible versions
-   **Single source**: pyproject.toml remains the source of truth

### Alternative: requirements.in

If you prefer, you can keep `requirements.in` as an intermediate step:

```bash
# Edit requirements.in manually, then compile
pip-compile --output-file=requirements.txt requirements.in
```

However, the direct pyproject.toml approach is recommended to avoid duplication.
