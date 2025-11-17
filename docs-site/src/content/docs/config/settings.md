---
title: Settings
description: Configure sup CLI settings
---

# Settings

Configure sup CLI behavior and preferences.

## Configuration File

sup stores configuration in `~/.config/sup/config.yaml`:

```yaml
source_workspace_id: 123
target_workspace_id: 456
output_format: table
theme: emerald
```

## Environment Variables

```bash
# Authentication
export PRESET_API_TOKEN="your-token"
export PRESET_API_SECRET="your-secret"

# Output preferences
export SUP_OUTPUT_FORMAT="json"
export SUP_THEME="emerald"
```

## Commands

View current configuration:
```bash
sup config show
```

Set a configuration value:
```bash
sup config set target-workspace-id 789
```

Reset to defaults:
```bash
sup config reset
```