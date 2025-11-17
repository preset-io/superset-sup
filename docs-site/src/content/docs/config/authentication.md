---
title: Authentication
description: Authentication methods for sup CLI
---

# Authentication

sup CLI supports multiple authentication methods for connecting to Superset and Preset workspaces.

## Preset.io Authentication

### API Token (Recommended)

Get your API credentials from [Preset Settings](https://preset.io/settings/api-tokens).

```bash
export PRESET_API_TOKEN="your-token"
export PRESET_API_SECRET="your-secret"
```

### JWT Token

For advanced users with JWT access:

```bash
export PRESET_JWT_TOKEN="your-jwt-token"
```

## Self-hosted Superset

### Username/Password

```bash
export SUPERSET_URL="https://your-superset.com"
export SUPERSET_USERNAME="admin"
export SUPERSET_PASSWORD="password"
```

### Session Token

If you have an existing session:

```bash
export SUPERSET_SESSION_TOKEN="session-token"
```

## Credential Storage

sup can store credentials securely:

```bash
# Store credentials
sup auth login

# Clear stored credentials
sup auth logout
```

## Testing Authentication

Verify your authentication:

```bash
sup workspace list
```

If authentication is successful, you'll see your available workspaces.