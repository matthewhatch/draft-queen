# Poetry Setup Guide

This project supports both Poetry (recommended) and traditional pip/virtualenv dependency management.

## Why Poetry?

Poetry provides several advantages:

- **Deterministic builds** - `poetry.lock` ensures reproducible environments
- **Dependency resolution** - Automatically resolves complex dependency trees
- **Virtual environment isolation** - Built-in venv management
- **Easy publishing** - Simple package publishing to PyPI
- **Tool unification** - Combines pip, venv, and requirements management
- **Clean syntax** - `pyproject.toml` is more readable than `requirements.txt`

## Installation

### Install Poetry (macOS/Linux/WSL)

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### Install Poetry (Windows)

```bash
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

### Verify Installation

```bash
poetry --version
# Poetry (version 1.7.1)
```

Add Poetry to PATH if needed:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Basic Commands

### Project Setup

```bash
# Clone and navigate to project
cd /home/parrot/code/draft-queen

# Install all dependencies (creates .venv)
poetry install

# Activate Poetry shell
poetry shell

# Deactivate Poetry shell
exit
```

### Dependency Management

```bash
# Add a production dependency
poetry add requests==2.31.0

# Add a dev dependency
poetry add --group dev pytest-mock

# Add with version constraint
poetry add "fastapi>=0.100,<0.105"

# Update dependencies
poetry update

# Update specific dependency
poetry update sqlalchemy

# Show installed packages
poetry show

# Show package info
poetry show fastapi
```

### Running Commands

```bash
# Run commands within Poetry environment
poetry run pytest tests/
poetry run black data_pipeline/
poetry run mypy data_pipeline/
poetry run python main.py

# Or activate shell first
poetry shell
pytest tests/
black data_pipeline/
exit  # Exit Poetry shell
```

## Project Structure (pyproject.toml)

The `pyproject.toml` file defines:

### Project Metadata
```toml
[tool.poetry]
name = "nfl-draft-queen"
version = "0.1.0"
description = "NFL Draft Analysis Internal Data Platform"
authors = ["Your Name <you@example.com>"]
```

### Dependencies
```toml
[tool.poetry.dependencies]
python = "^3.9"
fastapi = "0.104.1"
sqlalchemy = "2.0.23"
# ... more dependencies
```

### Dev Dependencies
```toml
[tool.poetry.group.dev.dependencies]
pytest = "7.4.3"
black = "23.12.0"
mypy = "1.7.1"
# ... more dev dependencies
```

### Tool Configurations
```toml
[tool.black]
line-length = 100

[tool.mypy]
python_version = "3.9"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

## Workflow Scenarios

### Scenario 1: First-Time Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd draft-queen

# 2. Install dependencies
poetry install

# 3. Activate environment
poetry shell

# 4. Configure .env
cp .env.example .env
nano .env

# 5. Setup database
createdb nfl_draft
python -m alembic upgrade head

# 6. Run tests to verify
pytest tests/unit/ -v

# 7. Exit Poetry shell
exit
```

### Scenario 2: Add New Dependency

```bash
# 1. Enter Poetry shell
poetry shell

# 2. Add dependency
poetry add pandas==2.1.3

# 3. Use in code
import pandas as pd

# 4. Test
pytest tests/ -v

# 5. Exit
exit

# Note: poetry.lock is automatically updated
```

### Scenario 3: Update Dependencies

```bash
# 1. Check for outdated packages
poetry show --outdated

# 2. Update all dependencies
poetry update

# 3. Or update specific package
poetry update sqlalchemy

# 4. Test to ensure compatibility
poetry run pytest tests/ -v

# 5. Commit poetry.lock
git add poetry.lock
git commit -m "Update dependencies"
```

### Scenario 4: Collaborate with Team

```bash
# Team member clones repo
git clone <repo-url>
cd draft-queen

# Install exact same versions from poetry.lock
poetry install

# No need to worry about different versions!
```

## Poetry vs pip/virtualenv

### Poetry Approach
```bash
# Single command does everything
poetry install

# Lock file ensures reproducibility
git add poetry.lock  # Share exact versions with team
```

### Traditional Approach
```bash
# Multiple steps
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip freeze > requirements.txt
```

## Migrating from pip to Poetry

If you have an existing `requirements.txt`:

### Option 1: Let Poetry Handle It

```bash
# Poetry will read requirements.txt if you don't have pyproject.toml
poetry install

# Poetry will create pyproject.toml automatically
```

### Option 2: Manual Migration

```bash
# 1. Initialize new Poetry project
poetry init

# 2. Add dependencies one by one
poetry add fastapi uvicorn sqlalchemy

# Or install from requirements.txt
cat requirements.txt | xargs poetry add
```

## Troubleshooting

### Issue: "poetry: command not found"

**Solution:** Add Poetry to PATH
```bash
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Issue: "Poetry could not find a matching version"

**Solution:** Check version constraints in pyproject.toml
```bash
poetry lock --no-update  # Update lock file without changing constraints
poetry update             # Update to latest allowed versions
```

### Issue: "Python version not available"

**Solution:** Specify Python version
```bash
poetry env use python3.10
poetry install
```

### Issue: "ModuleNotFoundError" when running commands

**Solution:** Ensure you're in Poetry shell
```bash
poetry shell
python main.py

# Or use poetry run
poetry run python main.py
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - uses: snok/install-poetry@v1
      
      - run: poetry install
      
      - run: poetry run pytest tests/
      
      - run: poetry run black --check data_pipeline/
      
      - run: poetry run mypy data_pipeline/
```

## Virtual Environment Management

### List All Environments

```bash
poetry env list
```

### Remove Environment

```bash
poetry env remove python3.9
```

### Use Specific Python Version

```bash
poetry env use /usr/bin/python3.10
```

## Publishing (Future)

When ready to publish to PyPI:

```bash
# Update version in pyproject.toml
poetry version minor  # bumps 0.1.0 -> 0.2.0

# Build package
poetry build

# Publish to PyPI
poetry publish
```

## Resources

- [Poetry Documentation](https://python-poetry.org/docs/)
- [pyproject.toml Format](https://python-poetry.org/docs/pyproject/)
- [Dependency Specification](https://python-poetry.org/docs/dependency-specification/)
- [Managing Dependencies](https://python-poetry.org/docs/managing-dependencies/)

## Next Steps

1. **Install Poetry:** `curl -sSL https://install.python-poetry.org | python3 -`
2. **Run:** `poetry install`
3. **Activate:** `poetry shell`
4. **Work:** `pytest tests/`, `python main.py`, etc.
5. **Add deps:** `poetry add package_name`
6. **Commit:** `git add poetry.lock`

---

**Note:** Both `requirements.txt` and `pyproject.toml` are maintained for compatibility. Poetry is recommended for active development.
