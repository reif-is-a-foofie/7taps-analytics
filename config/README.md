# Configuration Directory

This directory contains all project configuration files.

## Contents

### Deployment Configuration
- `docker-compose.yml` - Docker services configuration for local development
- `Dockerfile` - Container build instructions aligned with Cloud Run deployment
- `runtime.txt` - Python runtime specification for legacy platforms

### Development Configuration
- `pyproject.toml` - Python project metadata and dependencies
- `.gitignore` - Git ignore patterns
- `.pre-commit-config.yaml` - Pre-commit hooks configuration

## Usage

Most tools will automatically find these files in the config directory. For tools that expect them at the root level, you may need to create symlinks or copy them temporarily.

## Note

These files were moved from the root directory to reduce clutter and improve organization.
