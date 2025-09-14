# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is `preset-cli`, a command-line interface for interacting with Preset (https://preset.io/) workspaces. The CLI allows users to:

- Run SQL queries against analytical databases in workspaces
- Import/export resources (databases, datasets, charts, dashboards)
- Sync from dbt Core/Cloud projects to Preset workspaces
- Manage users, teams, and workspace permissions
- Handle authentication via API tokens or JWT

The project provides three main CLI entry points:
- `preset-cli`: Legacy CLI for interacting with Preset workspaces
- `superset-cli`: Legacy CLI for standalone Superset instances
- `sup`: Modern, git-like CLI with beautiful UX (NEW - primary development focus)

## Architecture & Code Structure

### Legacy CLI Structure
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

### Modern sup CLI Structure (NEW)
```
src/sup/
├── main.py                    # Main sup entry point with beautiful branding
├── commands/                  # Entity-focused command modules
│   ├── workspace.py          # Workspace management + cross-workspace config
│   ├── database.py           # Database operations
│   ├── dataset.py            # Dataset management
│   ├── chart.py              # Chart pull/push with dependency management
│   ├── dashboard.py          # Dashboard operations
│   ├── query.py              # Saved query discovery
│   ├── user.py               # User management
│   ├── sql.py                # Direct SQL execution
│   └── config.py             # Configuration management
├── clients/                   # sup-specific client wrappers
│   ├── preset.py             # Wrapped PresetClient with sup UX
│   └── superset.py           # Wrapped SupersetClient with sup UX
├── config/                    # Modern Pydantic configuration
│   ├── settings.py           # Type-safe config models
│   └── paths.py              # Config file path resolution
├── filters/                   # Universal filtering system
│   ├── base.py               # UniversalFilters for all entities
│   └── chart.py              # Chart-specific filters
├── output/                    # Beautiful Rich output system
│   ├── styles.py             # Emerald green Preset branding
│   ├── formatters.py         # Output format handlers
│   ├── tables.py             # Rich table formatting
│   └── spinners.py           # Loading indicators
└── auth/                      # Authentication wrappers
    └── preset.py             # sup-compatible auth
```

### Legacy CLI Components

- **API Clients**: `PresetClient` and `SupersetClient` handle REST API interactions
- **Authentication**: Supports JWT tokens, API token/secret pairs, and credential storage
- **CLI Commands**: Built using Click framework with hierarchical command structure
- **Templating**: Uses Jinja2 for parameterized YAML configuration files
- **Sync Operations**: Bidirectional sync between filesystems and workspaces

### Modern sup CLI Components (NEW)

- **Entity Commands**: Chart, dashboard, dataset, database, user, workspace, query
- **Universal Filtering**: Consistent --mine, --name, --ids, --limit patterns across all entities
- **Pull/Push Operations**: Git-like asset lifecycle with dependency management
- **Cross-Workspace Support**: Enterprise target-workspace-id for multi-instance sync
- **Beautiful UX**: Rich tables, emerald branding, spinners, progress feedback
- **Configuration**: Type-safe Pydantic models with YAML persistence
- **Output Formats**: Rich tables, JSON, YAML, CSV, porcelain for automation

## sup CLI Development (Current Focus)

### sup Commands (Production Ready)
```bash
# Core workflow
sup workspace list                            # Beautiful Rich tables
sup workspace use 123                         # Set source workspace
sup workspace set-target 456                  # Set push target for cross-workspace sync
sup workspace show                            # Display source + target context

# SQL execution with multiple formats
sup sql "SELECT * FROM users LIMIT 5"        # Rich table output
sup sql "SELECT COUNT(*) FROM sales" --json  # JSON for automation

# Chart lifecycle management (COMPLETE PATTERN)
sup chart list --mine --limit 10              # Universal filtering
sup chart pull --mine                         # Pull charts + dependencies to ./assets/
sup chart push --workspace-id=456 --force     # Push to target workspace
sup chart sync ./templates --option env=prod  # Advanced templating (NEXT)

# Configuration management
sup config show                               # Display all current settings
sup config set target-workspace-id 789        # Set cross-workspace target
```

### sup Development Status
- ✅ **7 Entity Types Complete**: workspace, database, dataset, chart, dashboard, query, user
- ✅ **Chart Pull/Push Pattern**: Complete asset lifecycle with dependency management
- ✅ **Enterprise Features**: Cross-workspace sync, target configuration, safety confirmations
- ✅ **Production Tested**: Live integration with real Preset workspaces
- 🎯 **Next**: Chart sync for advanced templating workflows (bridges pull/push with legacy CLI power)

### dbt Integration Entity Distribution
**How dbt capabilities map to sup entities:**

- **`sup database sync`**: dbt profiles → Superset database connections
- **`sup dataset sync`**: dbt models → Superset datasets (schema, metrics, metadata)
- **`sup chart sync`**: Superset charts → dbt exposures (usage tracking)
- **`sup dashboard sync`**: Superset dashboards → dbt exposures (business context)

**Required sup config keys for dbt integration:**
```bash
# dbt Core
dbt-profiles-dir, dbt-project-dir

# dbt Cloud
dbt-cloud-account-id, dbt-cloud-project-id, dbt-cloud-job-id, dbt-cloud-api-token
```

## Legacy CLI Development Commands

### Environment Setup
```bash
# Using uv (preferred for fastest installation)
uv pip install -e '.[testing]'

# Or using make (which uses uv)
make install
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
