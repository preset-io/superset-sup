# `sup` - The Ultimate Superset CLI 🚀

## Vision: "Wassup?!" - Introducing `sup`

Transform the current `preset-cli` into **`sup`** - THE definitive command-line interface for Apache Superset and Preset, designed for both human users and AI agents. Think of it as the "gh" for GitHub, but for the Superset ecosystem.

## Current State Analysis

### What Works Well Today
- **Solid Foundation**: Robust API clients for both Preset and Superset
- **Core Functionality**: SQL execution, asset management, dbt sync capabilities
- **Authentication**: Multi-method auth (JWT, API tokens, username/password)
- **Export/Import**: Full asset lifecycle management
- **Templating**: Jinja2-powered configuration templating

### Critical Pain Points
1. **Old-School CLI Framework**: Click-based, verbose, not type-safe
2. **Cumbersome Configuration**: No persistent state management, repetitive workspace/database selection
3. **Poor Information Architecture**: Command hierarchy doesn't match Superset's mental model
4. **Limited Rich Output**: Plain text tables, no interactive elements or beautiful formatting
5. **Agent-Unfriendly**: No structured output formats (JSON), verbose interaction patterns

## The `sup` Vision: A Modern CLI Revolution

### Core Principles
1. **Data-First**: Make SQL execution and data access the primary use case
2. **Modern & Beautiful**: Best-in-class libraries (Typer, Rich, Pydantic) with stunning visuals
3. **Easily Stateful**: Smart defaults eliminate repetitive arguments
4. **Data-Oriented**: Focus on data exploration, analysis, and manipulation
5. **Agent-Friendly**: Perfect for coding assistants and automation workflows

### Modern CLI Experience

**ASCII Welcome & Branding**
```
██ ███████╗██╗   ██╗██████╗ ██╗
██ ██╔════╝██║   ██║██╔══██╗██║
   ███████╗██║   ██║██████╔╝██║
   ╚════██║██║   ██║██╔═══╝ ╚═╝
   ███████║╚██████╔╝██║     ██╗
   ╚══════╝ ╚═════╝ ╚═╝     ╚═╝

        🚀 The Ultimate Superset CLI 📊
          Ready to explore your data?
```

**CLI Color Palette**
```python
# Primary color scheme inspired by Superset's brand
COLORS = {
    # Primary colors
    "primary": "#20A7C9",      # Superset blue
    "secondary": "#1565C0",    # Darker blue
    "accent": "#00BCD4",       # Cyan accent

    # Status colors
    "success": "#4CAF50",      # Green
    "warning": "#FF9800",      # Orange
    "error": "#F44336",        # Red
    "info": "#2196F3",         # Blue

    # UI colors
    "text": "#FFFFFF",         # White text
    "text_dim": "#B0BEC5",     # Dim gray
    "border": "#37474F",       # Dark gray borders
    "background": "#263238",   # Dark background

    # Data visualization
    "chart_1": "#1F77B4",      # Blue
    "chart_2": "#FF7F0E",      # Orange
    "chart_3": "#2CA02C",      # Green
    "chart_4": "#D62728",      # Red
    "chart_5": "#9467BD",      # Purple
}

# Rich style mappings
RICH_STYLES = {
    "brand": "bold cyan",
    "success": "bold green",
    "error": "bold red",
    "warning": "bold yellow",
    "info": "bold blue",
    "dim": "dim white",
    "header": "bold magenta",
    "data": "cyan",
    "link": "blue underline"
}
```

**Best-in-Class Libraries Stack**
- **Typer 0.12+**: Modern CLI framework with automatic help and validation
- **Rich 13+**: Beautiful terminal formatting, tables, progress bars, syntax highlighting
- **Pydantic 2.0+**: Type-safe configuration and data validation
- **PyYAML**: YAML configuration file parsing (chosen over TOML)
- **Textual 0.50+**: Rich TUI interfaces for complex operations (future)
- **Click-completion**: Shell autocompletion for commands and arguments
- **Questionary**: Beautiful interactive prompts and selections
- **Halo**: Elegant terminal spinners and loading indicators

**GitHub CLI-Inspired Command Structure**
```bash
# Top-level commands (like `gh repo`, `gh issue`)
sup sql           # Execute SQL queries
sup workspace     # Workspace management
sup database      # Database operations
sup dataset       # Dataset operations
sup chart         # Chart operations
sup dashboard     # Dashboard operations
sup assets        # Asset management
sup config        # Configuration

# Subcommands follow consistent patterns
sup workspace list
sup workspace use <id>
sup workspace info

sup database list
sup database use <id>
sup database info <id>

sup sql "SELECT 1"
sup sql --interactive
sup sql --file query.sql
```

### Target Users
- **Superset Admins**: Managing assets, users, permissions across workspaces
- **Data Analysts**: Running SQL, exploring datasets, creating charts
- **Developers**: Integrating Superset into CI/CD, automation workflows
- **AI Agents**: Programmatic data access and workspace management
- **Migration Teams**: Moving dashboards between environments

## Technical Architecture

### Framework Migration: Click → Typer
```python
# Current (Click)
@click.command()
@click.option("--workspace-id", required=True)
@click.option("--database-id", required=True)
@click.option("--sql", required=True)
def sql_command(workspace_id, database_id, sql):
    # Implementation...

# New (Typer)
@app.command()
def sql(
    query: str = typer.Argument(..., help="SQL query to execute"),
    workspace_id: Optional[int] = None,
    database_id: Optional[int] = None,
    output: OutputFormat = OutputFormat.table,
) -> None:
    # Implementation with smart defaults from config...
```

### Configuration & State Management: YAML + Standard Locations

**State Storage Location:**
- **Global Config**: `~/.sup/config.yml` - Authentication, global preferences (following modern CLI conventions)
- **Project State**: `.sup/state.yml` - Project-specific workspace/database context
- **Environment Variables**: `SUP_*` prefix for CI/CD and containers

```python
# Global Configuration (~/.sup/config.yml)
class SupGlobalConfig(BaseSettings):
    # Preset Authentication (Primary Focus)
    preset_api_token: Optional[str] = None
    preset_api_secret: Optional[str] = None

    # Superset Authentication (Extensible Design)
    superset_instances: Dict[str, SupersetInstanceConfig] = {}

    # Global preferences
    output_format: OutputFormat = OutputFormat.table
    max_rows: int = 1000
    show_query_time: bool = True
    color_output: bool = True

    class Config:
        env_prefix = "SUP_"
        env_file = ".env"

# Superset instance configuration (for future extensibility)
class SupersetInstanceConfig(BaseSettings):
    url: str
    auth_method: Literal["username_password", "jwt", "oauth"] = "username_password"
    username: Optional[str] = None
    password: Optional[str] = None
    jwt_token: Optional[str] = None
    # Future: oauth_client_id, custom_headers, etc.

# Project State (.sup/state.yml)
class SupProjectState(BaseSettings):
    # Current context
    current_workspace_id: Optional[int] = None
    current_workspace_url: Optional[str] = None
    current_database_id: Optional[int] = None
    current_team: Optional[str] = None

    # Asset sync settings
    assets_folder: str = "./assets"
    sync_mode: SyncMode = SyncMode.bidirectional
    last_sync: Optional[datetime] = None

    class Config:
        config_file = ".sup/state.yml"
```

**Authentication Strategy:**
- **Phase 1 Focus**: Preset API tokens (proven, reliable)
- **Extensible Design**: Hook for future Superset instances
- **Future Goal**: Easy support for vanilla Superset dev environments
- **Reality**: Custom Superset setups may require manual configuration

## State Management Strategy

### **Two Types of State:**

**1. Static/Persistent State** (`~/.sup/config.yml`):
- Authentication credentials (optional - see security note)
- Global preferences (output format, colors, max rows)
- Named instance configurations

**2. Session/Context State** (Multiple layers):
- **Environment variables**: `SUP_WORKSPACE_ID`, `SUP_DATABASE_ID` (shell session scope)
- **Project state**: `.sup/state.yml` (project/directory scope)
- **CLI arguments**: `--workspace-id=123` (command scope)

### **State Management Approaches:**

**Option A: Typer + Environment Variables (RECOMMENDED)**
```python
# Typer doesn't manage state, but we can use a hybrid approach:

@app.command()
def workspace_use(workspace_id: int):
    """Set default workspace for current shell session."""
    # Update environment for current session
    os.environ["SUP_WORKSPACE_ID"] = str(workspace_id)

    # Optionally persist to project state
    if Path(".sup").exists():
        update_project_state({"current_workspace_id": workspace_id})

    # Show user how to persist across sessions
    console.print(f"✅ Using workspace {workspace_id} for this session")
    console.print(f"💡 To persist: export SUP_WORKSPACE_ID={workspace_id}")
```

**Option B: Smart Config File Updates**
```python
@app.command()
def workspace_use(workspace_id: int, persist: bool = False):
    """Set workspace context."""
    if persist:
        # Update ~/.sup/config.yml
        update_global_config({"current_workspace_id": workspace_id})
        console.print(f"✅ Workspace {workspace_id} saved globally")
    else:
        # Just set for current session
        os.environ["SUP_WORKSPACE_ID"] = str(workspace_id)
        console.print(f"✅ Using workspace {workspace_id} (session only)")
        console.print("💡 Add --persist to save permanently")
```

### **Security & Secrets Management:**

**Environment Variable Priority** (for security-conscious users):
```bash
# Users can set secrets in ~/.zshrc, ~/.bashrc, etc.
export SUP_PRESET_API_TOKEN="your_token_here"
export SUP_PRESET_API_SECRET="your_secret_here"

# sup respects these without storing in files
sup workspace list  # Uses env vars, no file storage needed
```

**File-based with User Choice:**
```python
@app.command()
def auth_setup():
    """Guide through authentication setup."""
    console.print("🔐 Authentication Setup")

    # Offer choices
    choice = Prompt.ask(
        "How would you like to store credentials?",
        choices=["env", "file", "skip"],
        default="env"
    )

    if choice == "env":
        console.print("Add these to your ~/.zshrc or ~/.bashrc:")
        console.print("export SUP_PRESET_API_TOKEN=your_token")
        console.print("export SUP_PRESET_API_SECRET=your_secret")
    elif choice == "file":
        # Store in ~/.sup/config.yml with user consent
        save_to_config_file()
    else:
        console.print("You can set SUP_* env vars manually")
```

**Configuration Hierarchy (High to Low Priority):**
1. CLI arguments (`--workspace-id=123`) - Command scope
2. Environment variables (`SUP_WORKSPACE_ID`) - Shell session scope
3. Project state (`.sup/state.yml`) - Directory scope
4. Global config (`~/.sup/config.yml`) - User scope
5. Interactive prompts (when no context available)

### Command Hierarchy: Superset Information Architecture

```bash
# Current preset-cli hierarchy
preset-cli --workspaces=... superset sql --database-id=1 --execute="SELECT 1"
preset-cli --workspaces=... superset export-assets /path
preset-cli --workspaces=... superset sync native /path

# New sup hierarchy - Entity-First Design
sup sql "SELECT * FROM sales LIMIT 10"                    # Smart defaults
sup sql "SELECT * FROM sales" --database-id=5 --json      # Override defaults
sup sql --interactive                                       # REPL mode

sup database list                                          # List all databases
sup database use 5                                         # Set default database
sup database info 5                                        # Database details

sup dataset list                                           # List datasets
sup dataset show 123                                       # Dataset schema
sup dataset sync dbt ./models/                           # Sync from dbt

sup chart list --dashboard-id=45                          # Charts in dashboard
sup chart export 123 ./chart.yaml                        # Export chart
sup chart create ./chart.yaml                            # Create from YAML

sup dashboard list                                         # List dashboards
sup dashboard export 45 ./dashboard/                     # Export dashboard
sup dashboard migrate 45 --to-workspace=staging          # Cross-workspace migration

sup workspace list                                         # List workspaces
sup workspace use staging                                  # Set default workspace
sup workspace info                                        # Current workspace details

sup config set workspace-id 123                          # Persistent config
sup config set database-id 5                             # Set defaults
sup config show                                           # Show current config
```

## Rich Output & Modern UX Design

**Colorful Help Text (GitHub CLI Style)**
```bash
$ sup --help

██ ███████╗██╗   ██╗██████╗ ██╗
██ ██╔════╝██║   ██║██╔══██╗██║
   ███████╗██║   ██║██████╔╝██║
   ╚════██║██║   ██║██╔═══╝ ╚═╝
   ███████║╚██████╔╝██║     ██╗
   ╚══════╝ ╚═════╝ ╚═╝     ╚═╝

        🚀 The Ultimate Superset CLI 📊

USAGE
  sup <command> <subcommand> [flags]

CORE COMMANDS
  sql             Execute SQL queries
  workspace       Manage workspaces
  database        Manage databases
  assets          Sync assets to/from folders

DATA COMMANDS
  dataset         Manage datasets
  chart           Manage charts
  dashboard       Manage dashboards

SETTINGS
  config          Manage configuration
  auth            Authenticate with Superset

FLAGS
  --help          Show help for command
  --version       Show version

EXAMPLES
  sup sql "SELECT COUNT(*) FROM users"
  sup workspace use 123
  sup assets export ./my-workspace

LEARN MORE
  Use 'sup <command> --help' for more information about a command.
```

**Beautiful Data Tables**
```python
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

def display_query_results(df: pd.DataFrame, query_time: float = None):
    # Beautiful table with borders and styling
    table = Table(
        title="📊 Query Results",
        show_header=True,
        header_style="bold blue",
        border_style="bright_blue",
        row_styles=["", "dim"]
    )

    # Add columns with smart styling
    for col in df.columns:
        table.add_column(col, style="cyan", no_wrap=False)

    # Add rows (limit display for large results)
    for _, row in df.head(100).iterrows():
        table.add_row(*[str(val) for val in row])

    # Show execution info
    if query_time:
        console.print(f"✅ Query executed in {query_time:.2f}s")

    console.print(table)

    if len(df) > 100:
        console.print(f"📋 Showing first 100 of {len(df):,} rows")
```

**Beautiful Spinners & Progress Bars**
```python
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from halo import Halo
import time

# Rich Progress with emojis and spinners
def sync_assets_with_progress():
    with Progress(
        SpinnerColumn("dots12", style="cyan"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(style="bar.back", complete_style="bar.complete"),
        TaskProgressColumn(),
        console=console
    ) as progress:
        # Scanning phase
        scan_task = progress.add_task("🔍 Scanning local assets...", total=None)
        time.sleep(2)
        progress.update(scan_task, description="✅ Found 25 assets")

        # Upload phase with progress bar
        upload_task = progress.add_task("📤 Uploading charts...", total=10)
        for i in range(10):
            time.sleep(0.5)
            progress.update(upload_task, advance=1)

        # Completion
        progress.update(upload_task, description="🎉 All assets synced!")

# Simple Halo spinners for quick operations
@contextmanager
def spinner(text: str, success: str = "✅ Done", error: str = "❌ Failed"):
    with Halo(text=text, spinner="dots12", color="cyan") as sp:
        try:
            yield sp
            sp.succeed(success)
        except Exception:
            sp.fail(error)
            raise

# Usage examples:
with spinner("🔐 Authenticating with Superset..."):
    authenticate()

with spinner("🗄️ Loading databases...", "📊 Found 5 databases"):
    load_databases()
```

**Emoji Usage Throughout CLI**
```python
# Command status indicators
EMOJI_STATUS = {
    "loading": "⏳",
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "rocket": "🚀",
    "chart": "📊",
    "database": "🗄️",
    "table": "📋",
    "sync": "🔄",
    "export": "📤",
    "import": "📥",
    "search": "🔍",
    "config": "⚙️",
    "workspace": "🏢",
    "sql": "💾",
    "dashboard": "📈",
    "user": "👤",
    "lock": "🔐",
    "link": "🔗",
    "fire": "🔥",
    "star": "⭐",
    "party": "🎉"
}

# Beautiful spinner variations
SPINNERS = {
    "dots": "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏",
    "arrows": "←↖↑↗→↘↓↙",
    "bouncing": "⠁⠂⠄⠂",
    "pulsating": "●○◉○",
    "clock": "🕐🕑🕒🕓🕔🕕🕖🕗🕘🕙🕚🕛"
}

# Command output examples:
console.print("🚀 Starting sup CLI...")
console.print("🔍 Searching for workspaces...")
console.print("📊 Found 3 databases in workspace")
console.print("✅ Query executed successfully in 0.24s")
console.print("🎉 Dashboard exported to ./my-dashboard/")
```

**Modern Interactive Elements**
- **Rich Progress Bars**: Real-time progress for exports/imports
- **Syntax Highlighting**: SQL queries, YAML configs, JSON output
- **Clickable Links**: Terminal links to Superset dashboards/charts
- **Smart Autocomplete**: Database/table/column name completion
- **Status Panels**: Bordered panels for important information
- **Color-Coded Output**: Success (green), warnings (yellow), errors (red)

## Implementation Strategy: Independent `sup` CLI

Create `sup` as its own entry point and package structure, sharing core functionality with the existing codebase where beneficial:

```
backend-sdk/
├── src/preset_cli/          # Legacy CLI (eventual deprecation)
├── src/shared/              # Shared core functionality
│   ├── auth/               # Authentication (reused by both CLIs)
│   ├── clients/            # API clients (Superset/Preset)
│   └── exceptions.py       # Common error handling
├── src/sup/                 # New independent CLI
│   ├── commands/           # Typer command modules
│   │   ├── sql.py          # SQL execution (primary focus)
│   │   ├── database.py     # Database selection/management
│   │   ├── workspace.py    # Workspace management
│   │   └── config.py       # Configuration commands
│   ├── config/             # Configuration management
│   │   ├── settings.py     # Pydantic models for YAML configs
│   │   └── paths.py        # Standard config locations
│   ├── output/             # Rich formatting & multiple outputs
│   │   ├── formatters.py   # Rich table, CSV, JSON, YAML
│   │   └── styles.py       # Colors, themes, emojis
│   └── main.py            # Entry point: `sup` command
├── pyproject.toml          # Both preset-cli and sup entry points
└── README.md              # Updated documentation
```

**Shared Code Strategy**: Factor out authentication and API clients to `src/shared/` for reuse, allowing `sup` to leverage proven functionality while maintaining independence for future innovation.

**Package Management**: Single `pyproject.toml` with multiple entry points during transition period, eventual migration to separate package when `sup` is mature and `preset-cli` is deprecated.

```toml
# pyproject.toml (monolithic approach)
[project.scripts]
preset-cli = "preset_cli.cli.main:preset_cli"
superset-cli = "preset_cli.cli.superset.main:superset_cli"
sup = "sup.main:app"  # New modern CLI

# All dependencies included - users get all 3 CLIs
install_requires = [
    # Existing preset-cli dependencies
    "click>=8.0.3",
    "requests>=2.26.0",
    "pyyaml>=6.0",
    "pandas>=1.3.5",
    "jinja2>=3.0.3",
    "marshmallow>=3.17.0",
    "backoff>=1.10.0",
    # ... other existing deps

    # sup-specific modern dependencies
    "typer>=0.12.0",
    "rich>=13.0.0",
    "pydantic>=2.0.0",
    "questionary>=1.10.0",
    "halo>=0.0.31",
]

# Simple install gets everything
# pip install preset-cli
# → preset-cli, superset-cli, sup all available
```

## Development Phases

### Phase 1: SQL-First POC (Data Access Layer)
**Core Goal**: Directed path from authentication → workspace selection → database selection → SQL execution

**Key Features:**
- [x] Setup independent `sup` CLI with Typer + Pydantic + YAML configs
- [x] Authentication flow: guide users to set API keys in `~/.sup/config.yml`
- [x] Workspace selection: `sup workspace list` and `sup workspace use <id>`
- [x] Database selection: `sup database list` and `sup database use <id>`
- [x] SQL execution: `sup sql "SELECT 1"` with smart context defaults
- [x] **Output formats**: Rich table (default), `--csv`, `--json`, `--yaml`, `--porcelain` flags
- [x] Token-efficient for agents: `sup sql "SELECT 1" --porcelain --json` minimizes response size
- [x] **LIVE PRODUCTION TESTING**: Successfully connected to real Preset workspace with 32 databases
- [x] **Performance optimized**: Cached hostnames, single auth, silent internal operations

**User Journey:**
```bash
# First time setup (Preset focus)
sup auth setup                           # Guides through Preset API key setup
sup workspace list                       # Shows available Preset workspaces
sup workspace use 123                    # Sets default workspace
sup database list                        # Shows databases in workspace
sup database use 5                       # Sets default database

# Now SQL just works
sup sql "SELECT COUNT(*) FROM users"                    # Rich table
sup sql "SELECT * FROM sales LIMIT 10" --csv           # CSV output
sup sql "SELECT id, name FROM users" --json            # JSON for agents

# Future: Superset instances
sup auth add-superset http://localhost:8088 --username admin --password admin
sup instance use localhost                              # Switch to local Superset
sup sql "SELECT 1"                                     # Works with any configured instance
```

**Success Criteria**: ✅ **ACHIEVED** - Complete authentication → SQL execution flow working in production with real Preset workspace

### Phase 2: Asset Management & DRY Improvements ✅ **IN PROGRESS**
**Core Goal**: Complete entity management with production-grade code quality

**Completed:**
- [x] **Dataset commands** - Full list/info/export with universal filtering
- [x] **Chart commands** - Complete chart management with clickable links
- [x] **Performance optimization** - Server-side pagination (50 result default)
- [x] **Multiple output formats** - `--json`, `--yaml`, `--porcelain` everywhere
- [x] **Beautiful spinners** - Halo integration with cyan branding
- [x] **Modern tooling** - Full pyproject.toml migration, ruff integration

**Next Steps:**
- [ ] **DRY improvements** - Command decorators, consolidated output handling
- [ ] **Dashboard commands** - Using proven template system
- [ ] **Interactive SQL REPL** - prompt-toolkit integration
- [ ] **Asset export/import** - Folder-based workflows with YAML

**Success Criteria**: ✅ **ACHIEVED** - All core entities working with production Preset workspace

### Phase 3: Advanced Data Operations
**Core Goal**: Professional SQL tooling and asset management

- [ ] Interactive SQL REPL with autocomplete and history
- [ ] Advanced output formatting (clickable links, live updates)
- [ ] Asset sync operations (`sup assets sync`, `sup assets diff`)
- [ ] Cross-workspace migration utilities
- [ ] Enhanced error handling with actionable messages

**Success Criteria**: Full asset lifecycle management + production-ready SQL tooling

### Phase 4: Agent Optimization & Polish
**Core Goal**: Perfect for AI agents and automation

- [ ] Comprehensive JSON output for all commands
- [ ] Batch operations and stdin support
- [ ] Advanced templating and bulk operations
- [ ] Community feedback integration
- [ ] Documentation and migration guides

## Key Commands Deep Dive

### SQL Execution - The Crown Jewel
```bash
# Interactive REPL with autocomplete
sup sql --interactive

# Quick queries with smart output
sup sql "SELECT COUNT(*) FROM users" --json
sup sql "SELECT * FROM sales WHERE date > '2024-01-01'" --csv > sales.csv

# Query with context
sup sql "SELECT * FROM users" --database-id=5 --schema=public --explain

# Save and reuse queries
sup sql "SELECT * FROM users WHERE active = true" --save=active_users
sup sql --load=active_users --format=json
```

## Asset Management System

### Folder-Based Asset Sync
```bash
# Initialize asset tracking in current directory
sup assets init                              # Creates .sup/state.toml + ./assets/

# Export entire workspace to local folder structure
sup assets export                            # Uses current workspace, exports to ./assets/
sup assets export --workspace-id=123 --folder=./my-workspace/

# Bi-directional sync (export + import)
sup assets sync                              # Sync current workspace with ./assets/
sup assets sync --workspace-id=prod --folder=./prod-assets/

# Import local changes back to workspace
sup assets import                            # Import ./assets/ to current workspace
sup assets import --workspace-id=staging --folder=./staging-assets/

# Track and manage changes
sup assets status                            # Show local vs remote differences
sup assets diff                              # Detailed diff of changes
sup assets reset                             # Reset local to match remote
```

### Folder Structure
```
./assets/
├── databases/
│   ├── main_db.yaml
│   └── analytics_db.yaml
├── datasets/
│   ├── users.yaml
│   ├── orders.yaml
│   └── sales_summary.yaml
├── charts/
│   ├── daily_revenue.yaml
│   ├── user_growth.yaml
│   └── top_products.yaml
├── dashboards/
│   ├── executive_summary.yaml
│   └── sales_analytics.yaml
└── .sup/
    ├── state.toml                          # Current workspace context
    ├── sync_state.json                     # Last sync timestamps
    └── templates/                          # Custom Jinja2 templates
```

### Agent-Friendly Asset Workflow
```bash
# Export specific dashboard for modification
sup dashboard export 45 --folder=./temp-dashboard/

# Agent modifies YAML files in ./temp-dashboard/
# ... AI agent edits chart configurations ...

# Import modified assets to different workspace
sup assets import --folder=./temp-dashboard/ --workspace-id=staging

# Cross-workspace migration
sup dashboard export 45 --workspace-id=prod --folder=./migration/
sup dashboard import ./migration/ --workspace-id=staging --overwrite
```

### Configuration That Works
```bash
# One-time setup
sup config set preset-api-token=xxx preset-api-secret=yyy
sup workspace list  # Shows available workspaces
sup workspace use my-prod-workspace
sup database list  # Shows databases in current workspace
sup database use main-db

# Now everything just works
sup sql "SELECT 1"  # Uses configured workspace + database
sup dashboard list  # Lists dashboards in configured workspace
```

## Why This Will Be Announcement-Worthy

1. **Paradigm Shift**: From configuration-heavy to intelligent defaults
2. **Modern UX**: Rich terminal interfaces that rival web apps
3. **Agent-First Design**: Perfect for the AI-assisted development era
4. **Cross-Platform Value**: Benefits both Preset customers and open-source Superset users
5. **Migration Superpower**: Makes moving between environments trivial
6. **Developer Experience**: Turns complex workflows into simple commands

## Development Notes

**Key Design Decisions Made:**
- ASCII art: Clean `'SUP!` without question mark (final choice)
- Config location: `~/.sup/config.yml` following modern CLI standards
- State management: Environment variables for session state, files for persistence
- Output formats: Rich table default, `--csv`/`--json`/`--yaml` top-level flags
- Authentication: Preset-first approach with extensible Superset hooks

**Critical Path:**
- Focus on authentication → workspace selection → database selection → SQL execution flow
- 2-minute setup goal from zero to running queries
- Token-efficient for AI agents with `--json` output

## Current Status Summary

### **Phase 1: ✅ COMPLETE**
- Modern CLI architecture with Typer + Rich + Pydantic
- Live production integration (697 datasets, 32 databases tested)
- Universal filtering system across all entity types
- Beautiful UX with spinners, clickable links, multiple output formats
- Performance optimized with smart caching and pagination

### **Phase 2: 🚧 IN PROGRESS**
- Dataset and chart commands fully functional
- DRY improvements documented for next iteration
- Modern tooling (pyproject.toml, ruff) implemented

### **Current Capabilities:**
```bash
# Live production examples:
sup sql "SELECT COUNT(*) FROM users" --porcelain --json
sup workspace list --yaml
sup dataset list --mine --name="*sales*" --limit=10
sup chart list --viz-type="*table*" --dashboard-id=45
```

## Community Impact

### For Preset Customers ✅ **Ready Now**
- Streamlined workflows for managing multiple workspaces
- Powerful automation capabilities with `--porcelain` mode
- Better developer experience than existing preset-cli

### For Open Source Superset 🚧 **Foundation Ready**
- Architecture supports self-hosted instances
- Asset management patterns established
- Ready for community extensions

### For AI Agents & Developers ✅ **Production Ready**
- Structured data access through simple commands
- Perfect automation with porcelain mode
- Minimal token usage for efficient AI integration

## Success Metrics

- **Adoption**: 1000+ weekly active users within 6 months
- **Community**: 50+ GitHub stars, community contributions
- **Usage Patterns**: 80% of commands use smart defaults (no explicit workspace/database)
- **Agent Integration**: Used in 10+ AI coding assistants and automation tools
- **Migration Impact**: 50% reduction in asset migration time

## Conclusion

`sup` represents a fundamental rethinking of how developers and agents interact with Superset. By combining modern CLI patterns, intelligent configuration management, and beautiful output formatting, we can create the tool that every Superset user wishes they had.

The monorepo approach allows us to innovate rapidly while maintaining backward compatibility, and the phased rollout ensures we deliver value quickly while building toward the full vision.

**This isn't just a CLI upgrade - it's a new paradigm for data workspace management. 🚀**
