---
title: Sync Configuration
description: Configure multi-workspace sync operations
---

# Sync Configuration

Configure advanced sync operations for multi-workspace deployments.

## Sync Configuration File

Create a `sync_config.yml` file:

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

target_defaults:
  overwrite: true
  jinja_context:
    environment: default
    company: ACME Corp

targets:
  - workspace_id: 456
    name: staging
    jinja_context:
      environment: staging
  - workspace_id: 789
    name: production
    jinja_context:
      environment: production
```

## Selection Strategies

### By IDs
```yaml
selection: ids
ids: [123, 456, 789]
```

### All Assets
```yaml
selection: all
```

### My Assets Only
```yaml
selection: mine
```

### With Filters
```yaml
selection: filtered
filters:
  name_pattern: "sales_*"
  tags: ["production", "reviewed"]
  modified_after: "2024-01-01"
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