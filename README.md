# 'sup! - Probably the Best Unofficial Apache Superset CLI 🚀

**A modern command-line interface for Apache Superset and Preset workspaces**

*Brought to you and fully compatible with Preset • For power users and AI agents*

---

## ✨ What is 'sup!?

'sup is a solid CLI for Apache Superset power users and their agents. It provides sectioned help, rich terminal formatting, and git-like workflows for managing Superset and Preset workspaces efficiently.

**[Screenshot of beautiful ASCII art and sectioned help will go here]**

## 🎯 Key Capabilities

• **Run any SQL** through Superset's data access layer - get results as rich tables, CSV, YAML or JSON
• **Backup and restore** charts, dashboards, and datasets with full dependency tracking
• **Synchronize assets** across Superset instances with Jinja2 templating for customization
• **Enrich metadata** to/from dbt Core/Cloud - more integrations to come
• **Automate workflows** and integrate with CI/CD pipelines
• **Perfect for scripting** and AI-assisted data exploration

## 🚀 Quick Start

### Installation

```bash
pip install superset-sup
```

### Getting Started

The beautiful sectioned help guides you through the perfect workflow:

```bash
# 🔧 Configuration & Setup
sup config auth          # Set up authentication credentials
sup config show          # Verify current settings

# 🔍 Direct Data Access
sup sql "SELECT COUNT(*) FROM users"           # Beautiful Rich table
sup sql "SELECT * FROM sales" --json           # JSON for agents
sup sql "SELECT * FROM sales" --csv            # CSV export

# 📊 Manage Assets
sup workspace list       # Find your workspace
sup workspace use 123    # Set default workspace
sup chart list --mine    # Your charts with server-side search
sup chart data 3628 --csv # Export chart data directly

# 🔄 Synchronize Assets Across Workspaces
sup sync create ./my_sync --source 123 --targets 456,789  # Git-ready sync
sup sync run ./my_sync --dry-run                          # Preview operations
sup sync run ./my_sync                                    # Execute sync
```

## 📋 Command Reference

### Configuration & Setup
- `sup config` - Beautiful configuration guide with sources, settings, and setup steps
- `sup config auth` - Set up authentication credentials
- `sup config show` - Display current configuration
- `sup config set workspace-id 123` - Set default workspace

### Direct Data Access
- `sup sql "query"` - Execute SQL with beautiful output
- `sup sql --interactive` - Interactive SQL session (coming soon)
- `sup sql "query" --json` - JSON output for automation
- `sup sql "query" --porcelain` - Machine-readable output

### Manage Assets
- `sup workspace list` - List available workspaces
- `sup database list` - Database operations
- `sup dataset list --search="users"` - Server-side search by table name
- `sup chart list --mine --search="revenue"` - Multi-field chart search
- `sup chart sql 3628` - Get compiled SQL behind any chart
- `sup chart data 3628 --csv` - Export actual chart data
- `sup dashboard list --search="exec"` - Dashboard title/slug search
- `sup query list --mine` - Discover saved queries
- `sup user list` - User management

### Synchronize Assets Across Workspaces
- `sup sync create` - Create sync configuration with templating
- `sup sync run --dry-run` - Preview sync operations
- `sup sync validate` - Validate sync configuration
- Enterprise cross-workspace workflows with Jinja2 templating

## 🎨 Beautiful Features

### Sectioned Help System
Commands are organized in logical sections that guide your workflow:
- **Configuration & Setup** → **Direct Data Access** → **Manage Assets** → **Synchronize**

### Rich Output Formats
- **Rich Tables**: Colorful, clickable tables with emerald green Preset branding
- **JSON**: Perfect for AI agents and automation (`--json`)
- **CSV**: Direct data export (`--csv`)
- **YAML**: Configuration-friendly format (`--yaml`)
- **Porcelain**: Machine-readable, no decorations (`--porcelain`)

### Filtering
Every entity command supports powerful, consistent filters:
```bash
--mine                      # Objects owned by current user
--name "pattern*"           # Name pattern matching with wildcards
--limit 50                  # Result pagination (default: 50)
--search "revenue"          # Server-side search (charts, dashboards, datasets)
--json                      # JSON output for automation
```

### Agent-Optimized
Perfect for AI assistants and automation:
```bash
sup chart data 3628 --json --limit=100        # Structured data access
sup sql "SELECT COUNT(*) FROM users" --json   # Direct SQL with JSON
sup dashboard list --search="exec" --porcelain # Machine-readable output
```

## 🔄 Git-like Asset Workflows

### Chart Lifecycle (Production Ready)
```bash
# Pull charts + dependencies to filesystem
sup chart pull --mine                         # Pull your charts + datasets + databases
sup chart pull --name="*revenue*"             # Pull revenue charts + dependencies
sup chart pull --id=3586                      # Pull specific chart + dependencies

# Push from filesystem to workspace
sup chart push                                # Push to configured target workspace
sup chart push --workspace-id=456             # Push to specific workspace
sup chart push --overwrite --force            # Push with overwrite, skip confirmations
```

### Advanced Sync Workflows
```bash
# Multi-target synchronization with templating
sup sync create ./templates --source 123 --targets 456,789,101
sup sync run ./templates --option env=prod    # Jinja2 templating for environments
sup sync run --bidirectional                 # Two-way sync with conflict resolution
```

## 🏗️ Architecture

### Modern Tech Stack
- **Typer 0.12+**: Type-safe CLI with automatic help generation
- **Rich 13+**: Beautiful terminal formatting and tables
- **Pydantic 2.0+**: Configuration validation and type safety
- **Pandas**: Data processing and multiple output formats

### Configuration
- **Global**: `~/.sup/config.yml` for user preferences
- **Project**: `.sup/state.yml` for project-specific settings
- **Environment**: `SUP_*` variables override everything
- **Priority**: Environment → Global → Project

### Enterprise Features
- **Cross-workspace sync**: Source workspace → multiple target workspaces
- **Asset dependencies**: Automatic resolution of charts → datasets → databases
- **Jinja2 templating**: Environment-specific customization
- **Git-ready**: YAML-based assets work perfectly with version control

## 🎯 Extra Features

### Chart SQL Access
Get the compiled SQL behind any chart - business logic included:
```bash
sup chart sql 3628
# Output: Complex SQL with filters, aggregations, joins - the actual query Superset runs
```

### Chart Data Export
Access actual chart results as structured data:
```bash
sup chart data 3628 --json     # Perfect for analysis, reporting, AI models
sup chart data 3628 --csv      # Direct CSV export
```

### Server-Side Search
Efficient search across all entity types:
- **Charts**: `--search` uses multi-field search (title, description, etc.)
- **Dashboards**: `--search` searches title and slug
- **Datasets**: `--search` searches table names
- All searches work with `--limit` for performance

## 🏠 Superset Compatibility

### Primary Focus: Preset-Hosted Instances
'sup is primarily designed for **Preset-hosted Superset instances** and has been extensively tested with Preset workspaces. All features work seamlessly with Preset's multi-workspace environment.

### Self-Hosted Superset
**Does it work with my Superset instance?** Most functionality should work, but depending on your authentication setup, you may need to tweak the code. We welcome contributions from the broader Superset community to improve compatibility.

**Preset-free mode**: A future version could remove multi-workspace constructs for single-instance Superset deployments. If you're interested in this, please contribute or open an issue.

### Contributing for Broader Compatibility
We're open to contributions that enable 'sup for the entire Superset community. Areas that likely need work for self-hosted instances:
- Authentication methods beyond Preset API tokens
- Single-instance mode (removing workspace concepts)
- Different API endpoint structures

## 🔐 Authentication

Multiple authentication methods supported:

### API Token (Recommended)
```bash
sup config auth  # Interactive setup
# Or set environment variables:
export SUP_PRESET_API_TOKEN="your-token"
export SUP_PRESET_API_SECRET="your-secret"
```

### Environment Variables
```bash
SUP_WORKSPACE_ID=123        # Default workspace
SUP_DATABASE_ID=5           # Default database
SUP_TARGET_WORKSPACE_ID=456 # Cross-workspace sync target
SUP_ASSETS_FOLDER=./assets  # Asset storage location
```

## 🎨 For Developers

### AI Agent Integration
'sup is designed to be AI-friendly:
- **Consistent patterns**: All commands follow the same filter patterns
- **Structured output**: JSON and porcelain modes for automation
- **Server-side filtering**: Efficient data access
- **Minimal tokens**: Optimized for AI context windows

### CI/CD Integration
```bash
# In your CI pipeline:
sup chart pull --mine --skip-dependencies     # Pull only charts
sup chart push --workspace-id=$PROD_WS --force # Deploy to production
sup sync run ./deploy --option env=production  # Multi-environment deploy
```

## 🆚 Legacy CLIs

'sup replaces and modernizes the legacy preset-cli and superset-cli tools while maintaining full compatibility with existing workflows. The legacy tools remain available but sup is the recommended modern experience.

### Migration Benefits
- **Beautiful UX**: Rich formatting vs plain text
- **Logical organization**: Sectioned help vs long command lists
- **Git-like workflows**: Intuitive pull/push vs complex export/import
- **Agent-optimized**: Perfect for AI assistants
- **Type-safe**: Modern Python with full type hints

## 🤝 Contributing

We welcome contributions! 'sup is built with modern Python practices:
- **Type hints throughout**: Full mypy compatibility
- **Rich testing**: Comprehensive test suite
- **Clean architecture**: Modular, extensible design
- **Beautiful code**: Ruff formatting, clean patterns

Visit [github.com/preset-io/superset-sup](https://github.com/preset-io/superset-sup) to contribute!

## 📄 License

[Insert license information]

---

*Built with ❤️ for the Apache Superset and Preset community*
