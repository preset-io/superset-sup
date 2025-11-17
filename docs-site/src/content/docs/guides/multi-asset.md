---
title: Multi-Asset Workflows
description: Managing complex multi-asset dependencies
---

# Multi-Asset Workflows

Learn how to manage complex workflows involving multiple asset types with dependencies.

## Understanding Dependencies

Superset assets have a dependency hierarchy:

```
Databases
    ↓
Datasets
    ↓
Charts
    ↓
Dashboards
```

## Pulling Assets with Dependencies

### Pull Dashboard with Everything

```bash
# Pull dashboard with all dependencies
sup dashboard pull --ids 123 --include-deps

# This pulls:
# - Dashboard 123
# - All charts in the dashboard
# - All datasets used by charts
# - Database connections (metadata only)
```

### Selective Dependency Pull

```bash
# Pull charts without datasets
sup chart pull --ids 456,789 --no-deps

# Pull datasets without database configs
sup dataset pull --mine --skip-databases
```

## Multi-Asset Sync Workflow

### 1. Create Sync Configuration

```yaml
# multi-asset-sync.yml
source:
  workspace_id: 123
  assets:
    dashboards:
      selection: ids
      ids: [100, 101]
      include_dependencies: true
    charts:
      selection: ids
      ids: [200, 201, 202]
      include_dependencies: true
    datasets:
      selection: all
      include_dependencies: false

targets:
  - workspace_id: 456
    name: target-workspace
```

### 2. Preview Changes

```bash
sup sync run multi-asset-sync.yml --dry-run
```

### 3. Execute Sync

```bash
sup sync run multi-asset-sync.yml
```

## Handling Conflicts

### Dataset Name Conflicts

When datasets have naming conflicts:

```bash
# Rename on push
sup dataset push --rename-pattern "DEV_{name}"

# Force overwrite
sup dataset push --force --overwrite
```

### Chart Ownership

Preserve or change ownership:

```bash
# Keep original owner
sup chart push --preserve-owner

# Assign to current user
sup chart push --assign-to-me
```

## Batch Operations

### Export Everything

```bash
# Export all assets from workspace
sup workspace export --all --output ./backup/

# Export specific types
sup workspace export --types charts,dashboards --output ./export/
```

### Import Bundle

```bash
# Import exported bundle
sup workspace import ./backup/ --workspace-id 456
```

## Dependency Resolution

sup automatically resolves dependencies in the correct order:

1. **Databases** are created/updated first
2. **Datasets** are created with database references
3. **Charts** are created with dataset references
4. **Dashboards** are created with chart references

## Best Practices

1. **Always use --dry-run** first to preview changes
2. **Version control** your sync configurations
3. **Document dependencies** in your sync config
4. **Use tags** to organize related assets
5. **Test in staging** before production sync
6. **Monitor logs** for dependency warnings

## Example: Full Migration

```bash
# 1. Export from source
sup workspace use source-workspace
sup workspace export --all --output ./migration/

# 2. Review exported assets
ls -la ./migration/assets/

# 3. Import to target
sup workspace use target-workspace
sup workspace import ./migration/ --force

# 4. Verify migration
sup dashboard list --limit 10
sup chart list --limit 10
```