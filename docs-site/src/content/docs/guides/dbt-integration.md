---
title: dbt Integration
description: Sync dbt models with Superset datasets
---

# dbt Integration

sup CLI can synchronize your dbt models with Superset datasets, keeping your analytics stack in sync.

## Prerequisites

- dbt Core or dbt Cloud project
- Superset/Preset workspace with database connections

## dbt Core Integration

### Setup

Configure dbt paths:

```bash
sup config set dbt-project-dir /path/to/dbt/project
sup config set dbt-profiles-dir ~/.dbt
```

### Sync Models to Datasets

```bash
# Sync all models
sup dataset sync-dbt

# Sync specific models
sup dataset sync-dbt --models staging.sales,marts.revenue

# With custom target
sup dataset sync-dbt --target production
```

## dbt Cloud Integration

### Setup

Configure dbt Cloud credentials:

```bash
sup config set dbt-cloud-account-id 12345
sup config set dbt-cloud-project-id 67890
sup config set dbt-cloud-job-id 11111
sup config set dbt-cloud-api-token "your-token"
```

### Sync from dbt Cloud

```bash
# Sync from latest run
sup dataset sync-dbt-cloud

# Sync from specific run
sup dataset sync-dbt-cloud --run-id 123456
```

## Mapping Configuration

Create a `dbt_mapping.yml` file:

```yaml
models:
  staging.customers:
    superset_dataset: "STG_CUSTOMERS"
    metrics:
      - name: customer_count
        expression: COUNT(DISTINCT customer_id)
      - name: total_revenue
        expression: SUM(revenue)
    
  marts.sales:
    superset_dataset: "SALES_FACT"
    time_column: order_date
    dimensions:
      - customer_id
      - product_id
      - region
```

## Exposures

Generate dbt exposures from Superset:

```bash
# Generate exposures YAML
sup chart export-exposures > models/exposures.yml

# Include in dbt project
sup chart export-exposures --output models/exposures/superset.yml
```

## Best Practices

1. **Use consistent naming** between dbt models and Superset datasets
2. **Document metrics** in dbt and sync to Superset
3. **Version control** your mapping configurations
4. **Test in staging** before syncing to production
5. **Use CI/CD** to automate sync on dbt runs