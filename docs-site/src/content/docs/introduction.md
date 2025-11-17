---
title: Introduction
description: Get started with sup CLI
---

# Introduction to sup CLI

`sup` is a beautiful, modern command-line interface for Apache Superset and Preset workspaces. It provides a git-like workflow for managing your analytics assets.

## Why sup?

- **Familiar Interface**: Git-like commands (pull, push, sync)
- **Beautiful Output**: Rich tables with emerald branding
- **Enterprise Features**: Cross-workspace sync, JWT auth
- **Type Safety**: Built with Pydantic for reliability
- **Fast**: Optimized for performance

## Core Concepts

### Workspaces
A workspace is your Superset or Preset instance. You can work with multiple workspaces and sync assets between them.

### Assets
Assets are your Superset resources:
- **Databases**: Data source connections
- **Datasets**: Virtual tables and metrics
- **Charts**: Visualizations
- **Dashboards**: Collections of charts
- **Queries**: Saved SQL queries

### Workflows
sup supports three main workflows:
1. **Pull**: Download assets from workspace to local files
2. **Push**: Upload local assets to a workspace
3. **Sync**: Coordinate assets across multiple workspaces

## Next Steps

- [Install sup CLI](/installation/)
- [Quick Start Guide](/quick-start/)
- [Browse Commands](/commands/workspace/)