---
title: Cross-Workspace Sync
description: Learn how to sync assets between multiple workspaces
---

# Cross-Workspace Sync

Cross-workspace sync allows you to move assets between different Superset or Preset workspaces, perfect for development-to-production workflows.

## Basic Workflow

### 1. Set Source and Target Workspaces

```bash
# Set source workspace
sup workspace use 123

# Set target workspace
sup workspace set-target 456
```

### 2. Pull from Source

```bash
# Pull specific dashboards
sup dashboard pull --ids 789,790

# Pull charts with dependencies
sup chart pull --mine --include-deps
```

### 3. Push to Target

```bash
# Push to target workspace
sup dashboard push --workspace-id 456 --force
```

## Advanced Sync Configuration

### Multi-Target Sync

Create a sync configuration for multiple targets:

```yaml
# sync_config.yml
source:
  workspace_id: 123
  assets:
    dashboards:
      selection: ids
      ids: [789, 790]
    charts:
      selection: all

targets:
  - workspace_id: 456
    name: staging
  - workspace_id: 789
    name: production
```

Run the sync:

```bash
sup sync run ./sync_config.yml
```

## Best Practices

1. **Always pull before push** to ensure you have the latest version
2. **Use --dry-run** to preview changes before applying
3. **Version control your sync configs** for reproducibility
4. **Test in staging** before pushing to production

## Common Issues

### Dependency Conflicts

When pushing assets with dependencies:
- Datasets must exist before charts
- Databases must exist before datasets
- Use `--include-deps` to automatically handle dependencies

### Permission Errors

Ensure your API credentials have:
- Read access to source workspace
- Write access to target workspace
- Admin permissions for database connections
