# Asset Management System Design for `sup`

## Overview

The asset management system provides comprehensive CRUD operations for Superset/Preset entities with a focus on:
- **Cohesive filtering** across all entity types
- **Consistent command patterns** for predictable UX
- **Folder-based workflows** for version control and collaboration
- **Production automation** with porcelain mode support

## Core Entities

### Primary Assets
- **datasets** - Tables, views, and data sources
- **charts** - Visualizations and queries
- **dashboards** - Collections of charts and content
- **databases** - Connection configurations

### Meta Assets (Future)
- **users** - User accounts and permissions
- **roles** - Access control definitions
- **teams** - Group management

## Universal Command Pattern

### Structure: `sup <entity> <action> [filters] [options]`

```bash
# Core pattern examples
sup dataset list --mine --name="sales*"
sup chart export 123 --folder=./charts/
sup dashboard import ./assets/dashboards/executive.yaml --overwrite
```

## Universal Filtering System

### **Core Filters (All Entities)**
```bash
--id <id>                    # Single ID filter
--ids <id1,id2,id3>         # Multiple IDs (comma-separated)
--name <pattern>            # Name pattern matching (supports wildcards *)
--mine                      # Objects owned by current user
--team <team_id>            # Objects owned by specific team
--created-after <date>      # Created after date (YYYY-MM-DD)
--modified-after <date>     # Modified after date (YYYY-MM-DD)
--limit <n>                 # Limit number of results
```

### **Entity-Specific Filters**
```bash
# Datasets
--database-id <id>          # Filter by database
--schema <name>             # Filter by schema
--table-type <type>         # table, view, etc.

# Charts
--dashboard-id <id>         # Charts in specific dashboard
--viz-type <type>           # Visualization type (bar, line, etc.)
--dataset-id <id>           # Charts using specific dataset

# Dashboards
--published                 # Only published dashboards
--draft                     # Only draft dashboards
--folder <path>             # Dashboards in specific folder
```

## Universal Options

### **Output Control**
```bash
--json                      # JSON output
--csv                       # CSV output
--yaml                      # YAML output
--porcelain                 # Machine-readable (no decorations)
--limit <n>                 # Max results to return (default: 50)
--page <n>                  # Page number (1-based, default: 1)
--results <n>               # Results per page (aligns with API page_size)
--order <field>             # Sort by field (name, created, modified, id)
--desc                      # Sort descending (default: ascending)
```

## Pagination Strategy

### **Server-Side vs Client-Side Filtering**

**Server-Side (Preferred for Performance):**
- Use Superset API's built-in filtering for basic operations
- Leverage `page` and `page_size` parameters
- More efficient for large datasets (697+ datasets)

**Client-Side (Required for Complex Filters):**
- Pattern matching (`--name="sales*"`)
- Cross-field filtering that API doesn't support
- Custom logic like `--mine` with multiple owner fields

### **Hybrid Approach (Best of Both Worlds):**
```python
# 1. Build server-side API parameters (aligned with Superset API)
def build_api_params(filters: UniversalFilters, entity_type: str) -> dict:
    """Build API parameters that align with Superset's get_resources method."""
    api_params = {}

    # Pagination (always use for performance)
    page_size = filters.limit if filters.limit else 50
    api_params["page_size"] = page_size

    if filters.page:
        api_params["page"] = filters.page - 1  # API uses 0-based pages
    elif filters.offset:
        api_params["page"] = filters.offset // page_size

    # Ordering (API format)
    if filters.order:
        order_mapping = {
            "chart": {"name": "slice_name", "created": "created_on", "modified": "changed_on"},
            "dataset": {"name": "table_name", "created": "created_on", "modified": "changed_on"},
            "dashboard": {"name": "dashboard_title", "created": "created_on", "modified": "changed_on"},
        }
        field_map = order_mapping.get(entity_type, {})
        api_params["order_column"] = field_map.get(filters.order, filters.order)
        api_params["order_direction"] = "desc" if filters.desc else "asc"

    return api_params

# 2. Use hybrid filtering approach
api_params = build_api_params(filters, "chart")
charts = client.get_charts(**api_params)  # Server-side: pagination + ordering

# 3. Apply only complex client-side filters (pattern matching, etc.)
if filters.name or filters.mine or filters.viz_type:
    charts = apply_chart_filters(charts, filters, current_user_id)
```

### **Performance Impact:**
- **Before**: Fetch 1000+ charts → filter to 50 (slow)
- **After**: Fetch 50 charts → apply complex filters (fast)
- **Result**: ~10x faster response times

### **Common Ordering Fields:**
- **name** - Entity name (table_name, slice_name, dashboard_title)
- **created** - Creation date (created_on)
- **modified** - Last modified date (changed_on)
- **id** - Entity ID
- **owner** - Owner name (for datasets/charts/dashboards)

### **Implementation Notes:**
- **Default page_size: 100** - Balance between performance and completeness
- **Auto-pagination**: Fetch all pages when no limit specified
- **Smart caching**: Cache recent results for repeated operations
- **Progress indication**: Beautiful Halo spinners with cyan branding
- **Consistent output formats**: `--json`, `--yaml`, `--porcelain` everywhere

## Clickable Terminal Links

### **Rich Table Integration**
All entity tables include clickable terminal links for seamless CLI ↔ GUI workflows:

**Link Patterns:**
- **ID Column**: Links to API endpoint (`/api/v1/{entity}/{id}`) for developers
- **Name Column**: Links to UI page for visual exploration

### **Entity-Specific Link Mapping**

#### **Datasets**
```bash
# ID → API endpoint
https://{hostname}/api/v1/dataset/{id}

# Name → Dataset exploration page
https://{hostname}/tablemodelview/list/?_flt_1_table_name={name}
# OR (if explore_url provided in response)
https://{hostname}{explore_url}
```

#### **Charts**
```bash
# ID → API endpoint
https://{hostname}/api/v1/chart/{id}

# Name → Chart editor/viewer
https://{hostname}/superset/explore/?slice_id={id}
```

#### **Dashboards**
```bash
# ID → API endpoint
https://{hostname}/api/v1/dashboard/{id}

# Name → Dashboard viewer
https://{hostname}/superset/dashboard/{id}/
```

### **Implementation Strategy**
1. **Extract hostname** from workspace context (already cached)
2. **Use Rich's link functionality** for terminal clickability
3. **Detect explore_url** in API responses when available
4. **Fallback patterns** when specific URLs not provided
5. **Porcelain mode**: Plain text (no links) for automation

### **Benefits**
- **Seamless workflows**: CLI discovery → GUI deep dive
- **Developer experience**: Quick API access for debugging
- **User experience**: Visual exploration without context switching
- **Professional polish**: Enterprise-grade integration

## Major Discovery: Assets-Only Architecture 🔍

### **Critical Insight: Import/Export Should Be Centralized**
After investigating the existing CLI complexity, we discovered:

**❌ Problem with Per-Entity Import/Export:**
```bash
# This creates confusion and dependency hell:
sup dataset export 123                    # What about dependent charts?
sup chart export 456                      # What about dependent datasets?
sup dashboard export 789                  # What about dependent charts & datasets?
```

**✅ Solution: Centralized `sup assets` Commands:**
```bash
# All import/export operations under assets
sup assets export                          # Export everything with dependencies
sup assets export --charts=123,456        # Export specific charts + all dependencies
sup assets import ./workspace-backup/     # Import with dependency resolution
```

### **Implementation Strategy: Safe Wrapper Pattern**
**Reuse Existing Tested Logic (421 test functions!):**
- **Import existing functions** - `export_resource_and_unzip`, `import_resources`
- **Add sup UX layer** - Beautiful spinners, Rich output, universal filtering
- **Maintain safety** - Don't rewrite complex ZIP/Jinja/dependency logic
- **Focus on UX** - What makes sup better (consistency, beauty, agent-friendliness)

### **Benefits of Assets-Only Architecture:**
1. **✅ Conceptual clarity** - Assets = complex operations, Entities = simple CRUD
2. **✅ Dependency resolution** - Automatic handling of chart→dataset→database chains
3. **✅ User experience** - No confusion about which export command to use
4. **✅ Safety** - Reuse 421 existing tests, zero risk of breaking functionality
5. **✅ Universal filtering** - `--mine --name="*sales*"` works with asset operations

## Key Implementation Learnings

### **Spinner System (Halo + Rich)**
- **Beautiful animations**: `dots12` spinner with cyan branding
- **Smart context**: Success/failure states with emoji indicators
- **Porcelain compatibility**: Completely silent in automation mode
- **Progress updates**: Dynamic text updates during long operations

### **Authentication & Performance**
- **Hostname caching**: Store workspace hostname to avoid repeated API calls
- **Silent internal operations**: Suppress verbose messages for efficiency
- **Single authentication**: Avoid double auth per command execution
- **Smart client reuse**: Create clients once, use multiple times

### **Filtering Architecture**
- **Universal filters**: Consistent across all entity types (`--mine`, `--name`, `--ids`, etc.)
- **Entity-specific extensions**: Additional filters per entity type
- **Hybrid filtering**: Server-side when possible, client-side for complex patterns
- **DRY implementation**: Reusable filter parsing and application functions

### **Output Format Consistency**
- **Standard formats**: `--json`, `--yaml`, `--porcelain` everywhere
- **Rich tables**: Beautiful default human experience
- **Machine-readable**: Tab-separated porcelain for automation
- **Structured data**: JSON/YAML for config and API consumption

### **Table Layout & UX Design (Latest Learnings)**
- **4-column maximum**: Terminal width constraints require max 4 columns for readability
- **min_width only**: Let Rich auto-scale to fill terminal space (no max_width constraints)
- **Essential column priorities**: ID (8 chars), Name (15 chars), Type (8 chars), Dataset (12 chars)
- **Smart data display**: Show actual names (datasource_name_text) with ID fallbacks
- **Text wrapping enabled**: Long content like chart names wrap beautifully
- **Centralized color system**: All UI uses COLORS.* constants for consistent branding

### **Color System Architecture**
- **Zero hardcoded colors**: All "blue", "green", "cyan" replaced with semantic constants
- **Emerald green branding**: COLORS.primary (#10B981) throughout for Preset identity
- **Semantic color meanings**: success, warning, error, info, secondary for consistent UX
- **External library compatibility**: Halo spinners still use "cyan" string (library limitation)

### **Production Quality Improvements**
- **Type safety**: All mypy errors resolved, strict type checking enabled
- **Warning elimination**: Zero dotenv parsing warnings via proper pydantic-settings config
- **Short option consistency**: `-l` available across all entity commands that support --limit
- **Rich data experience**: Dataset names, clickable links, intelligent spacing

### **Proven Patterns for Replication**
1. **Create `{entity}_filters.py`** extending universal system
2. **Add `get_{entities}()` method** to SupSupersetClient
3. **Copy dataset command structure** - just change display fields
4. **Register in main.py** - One line addition
5. **Test with spinners and filtering** - Verify all formats work
6. **Follow 4-column table pattern** - ID, Name, Type, Primary Info for optimal readability

## DRY Improvement Recommendations

### **Current Status: Functional but Repetitive**

**✅ Excellent DRY Patterns:**
- Universal filtering system (`filters/base.py`)
- Shared output formatters (`output/formatters.py`)
- Reusable spinner system (`output/spinners.py`)
- Common configuration management (`config/settings.py`)
- Consistent auth and API patterns

**❌ Areas Needing DRY Improvements:**

#### **1. Massive Parameter Duplication (High Priority)**
```python
# Every list command has 15+ identical parameters!
# Example: chart.py, dataset.py both have:
id_filter: Annotated[Optional[int], typer.Option("--id", help="Filter by specific ID")] = None,
ids_filter: Annotated[Optional[str], typer.Option("--ids", help="Filter by multiple IDs (comma-separated)")] = None,
# ... 13 more identical lines
```

**Solution:** Create command decorators for universal filters:
```python
@with_universal_filters
@with_output_options
def list_charts(filters: UniversalFilters, output: OutputOptions, **chart_specific):
    # Much cleaner!
```

#### **2. Repeated Output Logic (Medium Priority)**
```python
# Same pattern in dataset.py, chart.py, workspace.py:
if porcelain:
    display_porcelain_list(...)
elif json_output:
    import json
    console.print(json.dumps(...))
elif yaml_output:
    import yaml
    console.print(yaml.safe_dump(...))
```

**Solution:** Extract into reusable function:
```python
def display_entity_results(items, format_type, porcelain, fields):
    # Single implementation for all entities
```

#### **3. Similar Table Display Functions (Medium Priority)**
- `display_datasets_table`
- `display_charts_table`
- `display_workspaces_table`

**Solution:** Generic table builder with entity-specific field configs:
```python
def display_entity_table(items, entity_config, hostname=None):
    # Universal table display with clickable links
```

#### **4. Error Handling Standardization (Low Priority)**
- Repeated error patterns across commands
- Consistent messaging but duplicated code

**Solution:** Error handling decorators and utilities

### **Implementation Priority for DRY Cleanup:**

1. **Command decorators** - Eliminate 80% of parameter duplication
2. **Output handler consolidation** - Single function for all format logic
3. **Generic table display** - Unified table rendering with entity configs
4. **Error handling utils** - Standardized error patterns

### **Benefits of DRY Improvements:**
- **Maintainability**: Change filtering logic once, affects all entities
- **Consistency**: Guaranteed identical behavior across commands
- **Extensibility**: Adding new entities becomes trivial
- **Code reduction**: ~50% less code while maintaining functionality

### **Import/Export Control**
```bash
--folder <path>             # Override SUP_ASSETS_FOLDER
--overwrite                 # Replace existing assets
--merge                     # Merge changes (default)
--dry-run                   # Preview changes without applying
--force                     # Skip confirmation prompts
--include-dependencies      # Include related assets (charts → datasets)
```

## Folder Structure & Environment Variables

### **Default Structure**
```
$SUP_ASSETS_FOLDER (default: ./assets/)
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
    ├── state.yml           # Workspace context
    ├── sync_state.json     # Last sync timestamps
    └── templates/          # Custom Jinja2 templates
```

### **Environment Variables**
```bash
SUP_ASSETS_FOLDER           # Override default ./assets/ location
SUP_WORKSPACE_ID            # Default workspace for operations
SUP_DATABASE_ID             # Default database for operations
SUP_AUTO_SYNC               # Auto-sync after imports (true/false)
SUP_DEFAULT_MERGE_STRATEGY  # overwrite, merge, skip
```

## Command Specifications

### **Dataset Commands**

#### `sup dataset list [filters] [options]`
```bash
# Examples
sup dataset list                                    # All datasets in current workspace
sup dataset list --mine                            # My datasets only
sup dataset list --database-id=1 --porcelain      # Machine-readable, specific DB
sup dataset list --name="sales*" --json           # Pattern matching, JSON output
sup dataset list --modified-after=2024-01-01      # Recent modifications
```

#### `sup dataset info <id> [options]`
```bash
# Examples
sup dataset info 123                              # Full dataset details
sup dataset info 123 --porcelain                  # Machine-readable details
sup dataset info 123 --json                       # JSON metadata
```

#### `sup dataset export <id|pattern> [options]`
```bash
# Examples
sup dataset export 123                            # Export to ./assets/datasets/
sup dataset export 123 --folder=./backup/         # Custom folder
sup dataset export --ids=1,2,3 --dry-run         # Multiple datasets, preview
sup dataset export --mine --include-dependencies  # All my datasets + related charts
```

#### `sup dataset import <file|folder> [options]`
```bash
# Examples
sup dataset import ./assets/datasets/users.yaml   # Single dataset
sup dataset import ./assets/datasets/ --overwrite # All datasets in folder
sup dataset import ./backup/ --merge --dry-run    # Preview merge operation
```

#### `sup dataset sync [options]`
```bash
# Examples
sup dataset sync                                   # Bi-directional sync with ./assets/
sup dataset sync --folder=./prod-assets/          # Custom folder
sup dataset sync --dry-run                        # Preview changes
```

## Implementation Strategy

### **✅ Phase 1: COMPLETED - Entity Foundation**
1. ✅ Universal filtering system infrastructure (DONE)
2. ✅ All entity commands (workspace, database, dataset, chart, dashboard, query) (DONE)
3. ✅ Beautiful Rich output with clickable links (DONE)
4. ✅ Live production testing with real Preset workspace (DONE)

### **✅ Phase 2: COMPLETED - Revolutionary Data Access**
1. ✅ Chart SQL access - `sup chart sql {id}` (BREAKTHROUGH!)
2. ✅ Chart data access - `sup chart data {id}` (BREAKTHROUGH!)
3. ✅ Saved query management - `sup query list/info` (DISCOVERY!)
4. ✅ DRY architecture with 80% code reduction (ARCHITECTURAL WIN!)

### **🚧 Phase 3: NEXT - Asset Import/Export (Safe Wrapper Approach)**
**Strategy**: Wrap existing tested logic rather than rewrite
1. **`sup assets` command group** - Centralized operations (not per-entity)
2. **Wrapper classes** - Import `export_resource_and_unzip`, `import_resources`
3. **Beautiful sup UX** - Add spinners, Rich output, universal filtering
4. **Safety first** - Reuse 421 existing tests, avoid complex ZIP/Jinja rewrite

### **🔮 Phase 4: FUTURE - Advanced Features**
1. Interactive SQL REPL with autocomplete
2. Cross-workspace migration utilities
3. Git integration for version control

## Technical Architecture

### **Reuse Existing Infrastructure**
- `preset_cli.cli.superset.export` - Proven export logic
- `preset_cli.api.clients.superset` - API client methods
- Existing YAML serialization and folder structures

### **New Components**
- Universal filter parser and validator
- Asset relationship mapping (charts → datasets → databases)
- Sync state management and conflict resolution
- Template system for customizable exports

## Success Metrics

- **Consistency**: Same filters work across all entity types
- **Automation**: Perfect for CI/CD with `--porcelain` mode
- **Migration**: Easy cross-workspace asset movement
- **Version Control**: Assets in git for team collaboration
