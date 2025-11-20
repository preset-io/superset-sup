---
title: Sync Configuration
description: Configure multi-workspace sync operations
---

# Sync Configuration

Configure advanced sync operations for multi-workspace deployments.

## Sync Configuration File

Create a `sync_config.yml` file to define source workspace, target workspaces, and asset selection criteria.

### Complete Example

```yaml
source:
  workspace_id: 123
  assets:
    dashboards:
      selection: ids
      ids: [254, 255]
      include_dependencies: true
    charts:
      selection: all
      include_dependencies: true
    datasets:
      selection: mine
      include_dependencies: false
    databases:
      selection: ids
      ids: [1, 2]
      include_dependencies: false

target_defaults:
  overwrite: false
  include_dependencies: true
  jinja_context:
    environment: default
    company: ACME Corp
    region: us-east-1

targets:
  - workspace_id: 456
    name: staging
    overwrite: true
    jinja_context:
      environment: staging
      database_host: staging-db.example.com
  - workspace_id: 789
    name: production
    jinja_context:
      environment: production
      database_host: prod-db.example.com
```

## Schema Reference

### Source Configuration

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workspace_id` | integer | Yes | Source workspace ID to pull assets from |
| `assets` | object | Yes | Asset types and selection criteria |

### Asset Types

Supported asset types under `source.assets`:
- `charts` - Chart configurations
- `dashboards` - Dashboard layouts
- `datasets` - Dataset/table configurations
- `databases` - Database connection configs

Each asset type uses the **Asset Selection** schema below.

### Asset Selection

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `selection` | string | `all` | Selection strategy: `all`, `ids`, `mine`, or `filter` |
| `ids` | array | null | Specific asset IDs (required when `selection: ids`) |
| `include_dependencies` | boolean | `true` | Include related dependencies (datasets, databases) |

### Target Defaults

Default configuration that applies to all targets unless overridden:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `overwrite` | boolean | `false` | Default overwrite behavior for push operations |
| `include_dependencies` | boolean | `true` | Default dependency inclusion behavior |
| `jinja_context` | object | `{}` | Default Jinja template variables |

### Target Configuration

Each target in the `targets` array:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `workspace_id` | integer | Yes | Target workspace ID to push assets to |
| `name` | string | No | Human-readable name for this target |
| `overwrite` | boolean | No | Override default overwrite (null = use defaults) |
| `jinja_context` | object | No | Target-specific Jinja variables (merged with defaults) |

**Note:** Target-specific `jinja_context` values override `target_defaults.jinja_context`.

## Selection Strategies

### All Assets
Pull all assets of the specified type:
```yaml
charts:
  selection: all
  include_dependencies: true
```

### By IDs
Pull specific assets by ID:
```yaml
dashboards:
  selection: ids
  ids: [254, 255, 256]
  include_dependencies: true
```

### My Assets Only
Pull only assets you own:
```yaml
datasets:
  selection: mine
  include_dependencies: false
```

### With Filters
Pull assets matching filter criteria:
```yaml
charts:
  selection: filter
  # Note: filter implementation pending
```

## Jinja Templating

Use Jinja templates in asset configurations:

```sql
-- In your SQL query
SELECT * FROM {{ environment }}_sales_data
WHERE company = '{{ company }}'
```

## Running Sync

```bash
# Dry run to preview changes
sup sync run ./sync_config.yml --dry-run

# Pull from source
sup sync run ./sync_config.yml --pull-only

# Push to targets
sup sync run ./sync_config.yml --push-only

# Full sync (pull then push)
sup sync run ./sync_config.yml
```
