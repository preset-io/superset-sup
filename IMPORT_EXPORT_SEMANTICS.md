# Import/Export Semantics in `sup` 📁↔️🌐

## Current Old CLI Semantics

### **Export (Workspace → Filesystem)**
```bash
# Export FROM workspace TO filesystem
preset-cli superset export-assets ./my-backup/
superset-cli https://superset.com export-assets ./assets/

# Meaning: Pull assets FROM remote workspace INTO local filesystem
# Direction: Workspace → Local Files
```

### **Import (Filesystem → Workspace)**
```bash
# Import FROM filesystem TO workspace
preset-cli superset import-rls ./rls.yaml
preset-cli superset import-roles ./roles.yaml
superset-cli https://superset.com sync native ./assets/

# Meaning: Push assets FROM local filesystem INTO remote workspace
# Direction: Local Files → Workspace
```

### **Semantic Clarity:**
- **Export** = "Download from workspace to filesystem"
- **Import** = "Upload from filesystem to workspace"
- **Sync** = "Two-way synchronization with conflict resolution"

## `sup` Import/Export Design 🎯

### **Consistent CLI Perspective: Filesystem is Home Base**

The CLI user works primarily from the filesystem, so semantics should be:
- **Export** = Get assets OUT of workspace, INTO local files
- **Import** = Put assets FROM local files, INTO workspace

### **Folder Structure (Based on Existing Patterns)**
```
./assets/                          # Default SUP_ASSETS_FOLDER
├── databases/
│   ├── main_db.yaml
│   ├── analytics_db.yaml
│   └── postgres_prod.yaml
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
    ├── state.yml               # Workspace context & sync state
    ├── sync_log.json          # Last sync timestamps & checksums
    └── templates/             # Custom Jinja2 templates
```

### **Command Semantics**

#### **1. Individual Asset Operations**
```bash
# Export: Workspace → Filesystem (download)
sup dataset export 123                        # Export to ./assets/datasets/users.yaml
sup chart export 456 --folder=./backup/      # Export to custom folder
sup dashboard export 789 --overwrite         # Overwrite existing file

# Import: Filesystem → Workspace (upload)
sup dataset import ./assets/datasets/users.yaml    # Import from file
sup chart import ./backup/charts/               # Import all charts in folder
sup dashboard import ./dashboard.yaml --merge       # Merge with existing
```

#### **2. Bulk Asset Operations**
```bash
# Export: Download entire workspace to filesystem
sup assets export                             # Export all to ./assets/
sup assets export ./workspace-backup/        # Export all to custom folder
sup assets export --asset-types=charts,datasets  # Export specific types

# Import: Upload from filesystem to workspace
sup assets import                             # Import all from ./assets/
sup assets import ./workspace-backup/        # Import from backup folder
sup assets import --dry-run                  # Preview without applying
```

#### **3. Sync Operations (Bi-directional)**
```bash
# Sync: Smart two-way synchronization
sup assets sync                              # Sync ./assets/ ↔ workspace
sup assets sync --mode=export-only          # Only download changes
sup assets sync --mode=import-only          # Only upload changes
sup assets diff                             # Show differences without syncing
```

## Architecture: Reusable Export/Import Logic 🏗️

### **DRY Pattern for Import/Export**

Since all entities (datasets, charts, dashboards) follow similar patterns, we can create reusable logic:

```python
# src/sup/assets/base.py
class AssetExporter:
    """Base class for exporting any asset type to YAML files."""

    def export_single(self, asset_id: int, folder: Path) -> Path:
        """Export single asset to YAML file."""

    def export_multiple(self, asset_ids: List[int], folder: Path) -> List[Path]:
        """Export multiple assets to YAML files."""

    def export_filtered(self, filters: UniversalFilters, folder: Path) -> List[Path]:
        """Export assets matching filters to YAML files."""

class AssetImporter:
    """Base class for importing any asset type from YAML files."""

    def import_single(self, file_path: Path, overwrite: bool = False) -> Dict:
        """Import single asset from YAML file."""

    def import_multiple(self, folder: Path, overwrite: bool = False) -> List[Dict]:
        """Import multiple assets from folder."""

# Entity-specific implementations
class DatasetExporter(AssetExporter):
    """Export datasets with dataset-specific logic."""

class DatasetImporter(AssetImporter):
    """Import datasets with validation and dependency resolution."""
```

### **Unified Command Pattern**
```python
# Clean command implementations using decorators + base classes
@app.command("export")
@with_universal_filters
@with_output_options
@with_export_options  # --folder, --overwrite, --dry-run
def export_datasets(
    filters: UniversalFilters,
    output: OutputOptions,
    export: ExportOptions,
    dataset_id: Optional[int] = None,
):
    """Export datasets - clean and consistent."""
    exporter = DatasetExporter(client, export.folder)

    if dataset_id:
        # Single asset export
        file_path = exporter.export_single(dataset_id)
        console.print(f"✅ Exported dataset {dataset_id} to {file_path}")
    else:
        # Bulk export using filters
        file_paths = exporter.export_filtered(filters)
        console.print(f"✅ Exported {len(file_paths)} datasets")
```

## YAML File Format Standards 📄

### **Individual Asset Files**
```yaml
# datasets/users.yaml
version: 1.0
asset_type: dataset
metadata:
  uuid: "12345678-1234-5678-9abc-123456789abc"
  created_on: "2024-01-15T10:30:00Z"
  created_by: "user@company.com"
  workspace_id: 123

spec:
  table_name: users
  database:
    database_name: "postgres_main"
    # Reference by name - resolved during import
  schema: public
  description: "User information table"
  columns:
    - column_name: id
      type: INTEGER
      is_dttm: false
    - column_name: email
      type: VARCHAR(255)
      is_dttm: false
  # ... full Superset dataset definition
```

### **Bulk Export Manifest**
```yaml
# .sup/export_manifest.yaml
version: 1.0
exported_at: "2024-01-15T10:30:00Z"
workspace:
  id: 123
  hostname: "company.preset.io"
  name: "Production Analytics"

assets:
  databases: 5
  datasets: 147
  charts: 423
  dashboards: 89

dependencies:
  # Track cross-references for import ordering
  charts:
    456: [dataset:123, database:1]  # Chart 456 depends on dataset 123, database 1
  dashboards:
    789: [chart:456, chart:457]     # Dashboard 789 depends on charts 456,457
```

## Import/Export Flow Architecture 🔄

### **Export Flow**
```
1. sup dataset export 123
   ↓
2. Fetch asset from Superset API
   ↓
3. Transform to YAML format
   ↓
4. Resolve references (database_name vs database_id)
   ↓
5. Write to ./assets/datasets/users.yaml
   ↓
6. Update .sup/sync_state.json with checksums
```

### **Import Flow**
```
1. sup dataset import ./assets/datasets/users.yaml
   ↓
2. Read & validate YAML file
   ↓
3. Resolve references (database_name → database_id lookup)
   ↓
4. Check for conflicts (UUID exists? overwrite?)
   ↓
5. Transform to Superset API format
   ↓
6. POST/PUT to Superset API
   ↓
7. Update .sup/sync_state.json with success
```

### **Sync Flow**
```
1. sup assets sync
   ↓
2. Compare local .sup/sync_state.json with workspace
   ↓
3. Identify: New, Modified, Deleted assets (both directions)
   ↓
4. Show diff to user with confirmation prompt
   ↓
5. Apply changes: Export new remote → Import new local
   ↓
6. Handle conflicts with merge strategies
   ↓
7. Update sync state with new checksums
```

## Existing Code Reuse 🔄

### **What We Can Reuse**
```python
# From preset_cli/cli/superset/export.py
- export_assets() logic for fetching from API
- YAML serialization with Jinja2 template handling
- File naming and folder structure patterns
- Asset dependency resolution

# From preset_cli/cli/superset/sync/native/command.py
- import_assets() logic for YAML → API transformation
- Conflict resolution strategies
- Progress logging and error handling
- Template rendering with Jinja2
```

### **What We'll Improve**
- **Universal filtering** instead of hardcoded ID lists
- **Rich progress displays** with spinners and beautiful output
- **Type safety** with Pydantic models for YAML validation
- **Consistent error handling** across all asset types
- **Agent-friendly** machine-readable output modes

## Command Examples 💡

### **Individual Asset Operations**
```bash
# Export specific assets
sup dataset export 123                       # Single dataset
sup chart export --ids=456,457,458          # Multiple charts
sup dashboard export --mine --name="*sales*" # Filtered export

# Import specific assets
sup dataset import ./assets/datasets/users.yaml
sup chart import ./backup/charts/           # Import folder
sup dashboard import ./dash.yaml --dry-run  # Preview import
```

### **Bulk Operations**
```bash
# Export workspace to filesystem
sup assets export                           # Export all to ./assets/
sup assets export ./prod-backup/           # Custom folder
sup assets export --mine --created-after=2024-01-01  # Filtered bulk export

# Import filesystem to workspace
sup assets import                           # Import all from ./assets/
sup assets import ./staging-assets/        # Import from custom folder
sup assets import --asset-types=datasets,charts  # Import specific types
```

### **Sync Operations**
```bash
# Two-way synchronization
sup assets sync                            # Smart sync with prompts
sup assets sync --auto-confirm             # No prompts, apply all changes
sup assets diff                           # Show changes without applying
sup assets reset                          # Reset local to match workspace
```

## Conclusion: Clean Semantics + DRY Architecture 🎉

### **Clear Semantics**
- ✅ **Export** = Download from workspace to filesystem
- ✅ **Import** = Upload from filesystem to workspace
- ✅ **Sync** = Intelligent two-way synchronization

### **DRY Architecture**
- ✅ **Reusable base classes** for export/import logic
- ✅ **Universal filtering** works with all asset types
- ✅ **Consistent YAML formats** across all entities
- ✅ **Shared progress/error handling** patterns

### **Improved UX**
- ✅ **Beautiful Rich output** with progress bars
- ✅ **Agent-friendly modes** with `--porcelain --json`
- ✅ **Smart conflict resolution** with user prompts
- ✅ **Dependency tracking** for proper import ordering

The import/export system will leverage all our DRY improvements (decorators, consolidated output, universal filtering) while providing a clean, intuitive interface that's both human-friendly and perfect for automation! 🚀
