# Configuration Directory

This directory contains all project configuration files.

## Contents

### Deployment Configuration
- `docker-compose.yml` - Docker services configuration
- `Dockerfile` - Container build instructions
- `Procfile` - Heroku/Railway process definitions
- `render.yaml` - Render deployment configuration
- `railway.json` - Railway deployment configuration
- `runtime.txt` - Python runtime specification

### Development Configuration
- `pyproject.toml` - Python project metadata and dependencies
- `.gitignore` - Git ignore patterns
- `.pre-commit-config.yaml` - Pre-commit hooks configuration

## Usage

Most tools will automatically find these files in the config directory. For tools that expect them at the root level, you may need to create symlinks or copy them temporarily.

## Note

These files were moved from the root directory to reduce clutter and improve organization.
