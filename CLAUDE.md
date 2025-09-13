# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is `preset-cli`, a command-line interface for interacting with Preset (https://preset.io/) workspaces. The CLI allows users to:

- Run SQL queries against analytical databases in workspaces
- Import/export resources (databases, datasets, charts, dashboards)
- Sync from dbt Core/Cloud projects to Preset workspaces
- Manage users, teams, and workspace permissions
- Handle authentication via API tokens or JWT

The project provides two main CLI entry points:
- `preset-cli`: For interacting with Preset workspaces
- `superset-cli`: For standalone Superset instances

## Architecture & Code Structure

```
src/preset_cli/
├── api/clients/          # API client implementations
│   ├── preset.py        # Preset API client
│   └── superset.py      # Superset API client
├── auth/                # Authentication modules
│   ├── preset.py        # Preset-specific auth
│   ├── superset.py      # Superset auth
│   ├── jwt.py           # JWT token handling
│   └── token.py         # Token management
├── cli/                 # CLI command implementations
│   ├── main.py          # Main preset-cli entry point
│   ├── superset/        # Superset-specific commands
│   │   ├── main.py      # superset-cli entry point
│   │   ├── export.py    # Export resources
│   │   ├── sql.py       # SQL execution
│   │   └── sync/        # Synchronization commands
│   │       ├── native/  # Native YAML sync
│   │       └── dbt/     # dbt project sync
│   └── export_users.py  # User export functionality
└── lib.py              # Shared utilities
```

### Key Components

- **API Clients**: `PresetClient` and `SupersetClient` handle REST API interactions
- **Authentication**: Supports JWT tokens, API token/secret pairs, and credential storage
- **CLI Commands**: Built using Click framework with hierarchical command structure
- **Templating**: Uses Jinja2 for parameterized YAML configuration files
- **Sync Operations**: Bidirectional sync between filesystems and workspaces

## Development Commands

### Environment Setup
```bash
# Create pyenv virtual environment and install dependencies
make pyenv
```

### Testing
```bash
# Run all tests with coverage
make test

# Run pytest directly with coverage
pytest --cov=src/preset_cli -vv tests/ --doctest-modules src/preset_cli
```

### Code Quality
```bash
# Run pre-commit hooks (linting, formatting, etc.)
make check

# Spell check documentation and code
make spellcheck
```

### Requirements Management
```bash
# Update requirements.txt from requirements.in
make requirements.txt

# Update dev-requirements.txt from dev-requirements.in
make dev-requirements.txt
```

### Clean Up
```bash
# Remove virtual environment
make clean
```

## CLI Usage Patterns

The CLI uses a common pattern:
1. Authentication (API tokens, JWT, or interactive prompts)
2. Workspace/team selection (interactive or via `--workspaces`/`--teams` flags)
3. Command execution with resource-specific options

Example command structure:
```bash
preset-cli --workspaces=https://workspace.preset.io/ superset [command] [options]
```

## Key Configuration Files

- **setup.cfg**: Main package configuration, dependencies, and pytest settings
- **Makefile**: Development workflow automation
- **pyproject.toml**: Build system configuration
- **.pre-commit-config.yaml**: Code quality hooks
- **tox.ini**: Testing environments configuration

## Authentication Flow

1. Check for JWT token in environment (`PRESET_JWT_TOKEN`)
2. Check for API credentials in environment (`PRESET_API_TOKEN`, `PRESET_API_SECRET`)
3. Look for stored credentials in system-dependent location
4. Prompt user interactively and optionally store credentials

## Testing Framework

- Uses pytest with coverage reporting
- Includes doctests in source modules
- Mock objects for API interactions
- Test coverage target configured in setup.cfg

## Dependencies

Key dependencies include:
- Click for CLI framework
- PyYAML for configuration parsing
- Jinja2 for templating
- SQLAlchemy for database operations
- Requests for HTTP clients
- Rich for terminal formatting