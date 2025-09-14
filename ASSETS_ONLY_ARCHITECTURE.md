# Assets-Only Import/Export Architecture 🏗️

## Brilliant Insight: Centralize Import/Export Under `sup assets` 💡

You're absolutely right! Since all entities are interconnected with dependencies, import/export should be **centralized under `sup assets`** commands only.

## The Problem with Entity-Level Import/Export ❌

### **What We Almost Did Wrong:**
```bash
# This creates complexity and confusion:
sup dataset export 123                    # What about dependent charts?
sup chart export 456                      # What about dependent datasets?
sup dashboard export 789                  # What about dependent charts & datasets?

# Users would ask:
# - "Why can't I export a chart with its dataset?"
# - "How do I know what dependencies I'm missing?"
# - "Why are there 3 different export commands?"
```

### **Dependency Hell:**
- Charts depend on Datasets
- Datasets depend on Databases
- Dashboards depend on Charts
- All have cross-references via UUIDs

## The Right Architecture: `sup assets` Only ✅

### **Clean Command Structure:**
```bash
# All import/export operations under assets
sup assets export                          # Export everything
sup assets export --charts=123,456        # Export specific charts + dependencies
sup assets export --dashboards=789        # Export dashboard + all dependencies
sup assets import ./workspace-backup/     # Import everything with dependency resolution

# Individual entities focus on CRUD, not import/export
sup dataset list --mine                   # List & filter (what sup does best!)
sup chart info 123                       # Inspect & analyze
sup dashboard clone 456 "New Name"       # Create & modify operations
```

## Reuse Strategy: Wrap Existing Tested Logic 🔄

### **Import Existing Functions Safely:**
```python
# src/sup/assets/core.py
from preset_cli.cli.superset.export import export_resource_and_unzip
from preset_cli.cli.superset.sync.native.command import import_resources
from preset_cli.api.clients.superset import SupersetClient

class SupAssetsManager:
    """Wrapper around existing tested import/export logic"""

    def __init__(self, client: SupSupersetClient):
        self.client = client
        # Reuse existing tested SupersetClient
        self.legacy_client = SupersetClient(client.baseurl, client.auth)

    def export_assets(
        self,
        asset_types: List[str] = None,
        ids: Dict[str, List[int]] = None,
        folder: Path = Path("./assets"),
        **filters
    ) -> ExportResult:
        """Export assets using existing tested logic with sup UX"""

        # Convert sup filters to old CLI format
        legacy_ids = self._filters_to_legacy_ids(filters, asset_types)

        with data_spinner("assets", silent=filters.get('porcelain')) as sp:
            # Use existing tested export function
            for asset_type in asset_types:
                export_resource_and_unzip(
                    self.legacy_client,
                    asset_type,
                    legacy_ids.get(asset_type, []),
                    folder / asset_type
                )

            sp.text = f"Exported to {folder}"

        return ExportResult(folder=folder, asset_types=asset_types)
```

### **Wrapper Pattern Benefits:**
1. **✅ Reuse 421 existing tests** - No need to retest ZIP/Jinja logic
2. **✅ Add sup's beautiful UX** - Spinners, Rich output, universal filtering
3. **✅ Maintain compatibility** - Old CLI continues working unchanged
4. **✅ Focus on UX innovation** - Spend time on what makes sup better

## Clean Command Design 🎨

### **Assets Command Group:**
```python
# src/sup/commands/assets.py
@app.command("export")
@with_universal_filters
@with_output_options
def export_assets(
    filters: UniversalFilters,
    output: OutputOptions,

    # Asset selection (replaces per-entity export commands)
    asset_types: Annotated[List[str], typer.Option("--types", help="Asset types to export")] = ["datasets", "charts", "dashboards"],
    folder: Annotated[Path, typer.Option("--folder", help="Export folder")] = Path("./assets"),

    # ID-based selection (for specific assets)
    dataset_ids: Annotated[Optional[str], typer.Option("--dataset-ids")] = None,
    chart_ids: Annotated[Optional[str], typer.Option("--chart-ids")] = None,
    dashboard_ids: Annotated[Optional[str], typer.Option("--dashboard-ids")] = None,
):
    """
    Export assets with automatic dependency resolution.

    Examples:
        sup assets export                                    # Export everything
        sup assets export --mine --types=charts,datasets    # My charts & datasets
        sup assets export --chart-ids=123,456               # Specific charts + dependencies
        sup assets export --folder=./backup/                # Custom folder
    """
    manager = SupAssetsManager.from_context(SupContext(), output.workspace_id)

    # Use universal filters + asset-specific IDs
    result = manager.export_assets(
        asset_types=asset_types,
        folder=folder,
        filters=filters,
        dataset_ids=parse_ids(dataset_ids),
        chart_ids=parse_ids(chart_ids),
        dashboard_ids=parse_ids(dashboard_ids),
    )

    # sup's beautiful output
    display_export_results(result, output)


@app.command("import")
@with_output_options
def import_assets(
    output: OutputOptions,
    folder: Annotated[Path, typer.Option("--folder")] = Path("./assets"),
    overwrite: Annotated[bool, typer.Option("--overwrite")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
):
    """
    Import assets from folder with dependency resolution.

    Examples:
        sup assets import                        # Import from ./assets/
        sup assets import --folder=./backup/    # Import from backup
        sup assets import --dry-run             # Preview without applying
    """
    manager = SupAssetsManager.from_context(SupContext(), output.workspace_id)

    result = manager.import_assets(
        folder=folder,
        overwrite=overwrite,
        dry_run=dry_run
    )

    display_import_results(result, output)
```

## Individual Entity Commands: CRUD Only 🔧

### **Remove Import/Export from Entities:**
```python
# src/sup/commands/dataset.py - Focus on what sup does best
@app.command("list")    # ✅ Keep - sup's universal filtering is superior
@app.command("info")    # ✅ Keep - sup's Rich output is beautiful
@app.command("create")  # ✅ Add - simple API operations
@app.command("clone")   # ✅ Add - useful everyday operations
@app.command("delete")  # ✅ Add - with confirmation prompts

# ❌ Remove export/import - moved to `sup assets`
# @app.command("export") - REMOVED
# @app.command("import") - REMOVED

# Same pattern for chart.py, dashboard.py, etc.
```

## Migration Path 🛤️

### **Phase 1: Implement Assets Commands**
1. Create `src/sup/commands/assets.py` with export/import
2. Build `SupAssetsManager` wrapper around existing logic
3. Test with existing test suite (should pass!)
4. Add beautiful sup UX (spinners, Rich output)

### **Phase 2: Remove Entity Import/Export**
1. Remove export/import from `dataset.py`, `chart.py`, etc.
2. Update documentation to point to `sup assets`
3. Add helpful error messages: "Use `sup assets export` instead"

### **Phase 3: Enhanced Assets Operations**
1. Add smart filtering: `sup assets export --mine --modified-after=2024-01-01`
2. Add dependency visualization: `sup assets deps 123`
3. Add migration tools: `sup assets migrate --from-workspace=123 --to-workspace=456`

## Benefits of This Architecture 🎉

### **✅ Conceptual Clarity**
- **Assets = Complex cross-entity operations** (import/export, migration)
- **Entities = Simple CRUD operations** (list, info, create, delete)

### **✅ Reuse Existing Tests**
- 421 test functions continue protecting the complex logic
- We add tests only for sup's wrapper layer
- Zero risk of breaking existing functionality

### **✅ User Experience**
- No confusion about which command to use for export/import
- Universal filtering works across all asset types
- Dependency resolution happens automatically

### **✅ Future Extensibility**
```bash
# Easy to add new asset operations
sup assets diff ./backup/                    # Compare local vs workspace
sup assets migrate --to-workspace=staging   # Cross-workspace migration
sup assets template ./template.yaml         # Templated asset creation
```

## Conclusion: Perfect Architecture! 🎯

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Analyze test coverage in old CLI codebase", "status": "completed", "activeForm": "Analyzing test coverage in old CLI codebase"}, {"content": "Create strategy for reusing old CLI logic safely", "status": "completed", "activeForm": "Creating strategy for reusing old CLI logic safely"}, {"content": "Redesign sup architecture with assets-only import/export", "status": "completed", "activeForm": "Redesigning sup architecture with assets-only import/export"}]
