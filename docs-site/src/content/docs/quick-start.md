---
title: Quick Start
description: Get up and running with sup CLI in minutes
---

# Quick Start

## 1. Set Your Workspace

First, list available workspaces:

```bash
sup workspace list
```

Set your active workspace:

```bash
sup workspace use 123
```

## 2. Explore Your Assets

List your charts:

```bash
sup chart list --mine
```

List dashboards:

```bash
sup dashboard list --limit 10
```

## 3. Pull Assets Locally

Pull charts with dependencies:

```bash
sup chart pull --ids 456,789
```

This creates a local `./assets/` directory with your charts and their dependencies.

## 4. Run SQL Queries

Execute queries directly:

```bash
sup sql "SELECT COUNT(*) FROM orders WHERE created_at > '2024-01-01'"
```

Export results:

```bash
sup sql "SELECT * FROM customers" --json > customers.json
```

## 5. Push to Another Workspace

Set a target workspace:

```bash
sup workspace set-target 456
```

Push your charts:

```bash
sup chart push --force
```

## Common Workflows

### Development to Production

```bash
# Pull from dev
sup workspace use dev-workspace
sup dashboard pull --ids 123

# Push to prod
sup workspace use prod-workspace
sup dashboard push
```

### Backup Assets

```bash
sup chart pull --all
sup dashboard pull --all
git add assets/
git commit -m "Backup analytics assets"
```

## Next Steps

- [Cross-Workspace Sync Guide](/guides/cross-workspace/)
- [Command Reference](/commands/workspace/)
