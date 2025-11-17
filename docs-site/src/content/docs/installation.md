---
title: Installation
description: How to install sup CLI
---

# Installation

## Requirements

- Python 3.8 or higher
- pip or uv package manager

## Install from PyPI

```bash
pip install superset-sup
```

Or using uv (faster):

```bash
uv pip install superset-sup
```

## Install from Source

```bash
git clone https://github.com/preset-io/superset-sup.git
cd superset-sup
pip install -e .
```

## Verify Installation

```bash
sup --version
```

## Authentication Setup

### Preset.io

Get your API credentials from [https://preset.io/settings/api-tokens](https://preset.io/settings/api-tokens)

```bash
export PRESET_API_TOKEN="your-token"
export PRESET_API_SECRET="your-secret"
```

### Self-hosted Superset

```bash
export SUPERSET_URL="https://your-superset.com"
export SUPERSET_USERNAME="admin"
export SUPERSET_PASSWORD="password"
```

## Next Steps

- [Quick Start Guide](/quick-start/)
- [Browse Commands](/commands/workspace/)