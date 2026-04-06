---
title: "Feature Parity"
description: "Legacy preset-cli to sup CLI feature parity mapping"
---

# Feature Parity: Legacy preset-cli → sup CLI

## preset-cli (team-level commands)

| Legacy Command | sup Equivalent | Status |
|---|---|---|
| `auth` | `sup config auth` | ✅ |
| `invite-users` | `sup user invite` | ✅ |
| `import-users` | `sup user push` | ✅ |
| `export-users` | `sup user pull` | ✅ |
| `sync-roles` | `sup role sync` | ✅ |
| `list-group-membership` | `sup group list` | ✅ |

## superset-cli (workspace-level commands)

| Legacy Command | sup Equivalent | Status |
|---|---|---|
| `sql` | `sup sql` | ✅ |
| `export-assets` | `sup chart/dashboard/dataset/database pull` | ✅ |
| `export-users` | `sup user list` | ✅ |
| `export-rls` | `sup rls pull` | ✅ |
| `export-roles` | `sup role pull` | ✅ |
| `export-ownership` | `sup ownership pull` | ✅ |
| `import-rls` | `sup rls push` | ✅ |
| `import-roles` | `sup role push` | ✅ |
| `import-ownership` | `sup ownership push` | ✅ |
| `import-assets` / `sync native` | `sup sync native` | ✅ |
| `sync dbt-core` | `sup dbt core` | ✅ |
| `sync dbt-cloud` | `sup dbt cloud` | ✅ |

## sup additions (no legacy equivalent)

| Command | Description |
|---|---|
| `sup workspace list/use/info/set-target/show` | Workspace context management |
| `sup database list/use/info/pull` | Database management + pull |
| `sup dataset list/info/pull/push` | Dataset discovery + pull/push |
| `sup chart list/info/pull/push` | Full chart lifecycle |
| `sup dashboard list/info/pull/push` | Full dashboard lifecycle |
| `sup query list/info` | Saved query discovery |
| `sup group sync/create` | SCIM group management |
| `sup sync run/create/validate` | Multi-target sync framework |
| `sup dbt list-models` | dbt model preview |
| `sup config show/set/env/init` | Modern config management |
