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

### **Proven Patterns for Replication**
1. **Create `{entity}_filters.py`** extending universal system
2. **Add `get_{entities}()` method** to SupSupersetClient
3. **Copy dataset command structure** - just change display fields
4. **Register in main.py** - One line addition
5. **Test with spinners and filtering** - Verify all formats work

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

### **Phase 1: Dataset Foundation**
1. Universal filtering system infrastructure
2. Dataset list/info/export/import commands
3. Folder structure creation and management
4. Test with real Preset workspace

### **Phase 2: Chart Operations**
1. Chart commands using dataset foundation
2. Chart → Dataset dependency handling
3. Visualization type filtering

### **Phase 3: Dashboard Management**
1. Dashboard commands with chart inclusion
2. Bulk export/import workflows
3. Cross-workspace migration tools

### **Phase 4: Advanced Features**
1. Asset sync with conflict resolution
2. Template system for custom exports
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
