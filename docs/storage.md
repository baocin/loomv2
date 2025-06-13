# Storage Architecture

## Overview

Loom uses **PostgreSQL 15** as the primary relational database for any structured, durable data.  
The decision to use vanilla Postgres (instead of TimescaleDB) dramatically reduces the
operational overhead and increases portability for contributors who may not need
time-series extensions.

*If you need time-series features in the future, you can enable the `timescaledb` extension at the
schema level without breaking compatibility.*

## Local Development

- A minimal single-node Postgres instance is deployed by default in `deploy/dev/postgres.yaml`.
- Credentials (database `loom`, user `loom`, password `loom`) are stored in a Kubernetes `Secret`.
- The database is exposed internally via `ClusterIP` (port 5432) and, through k3d port mapping,
  reachable at `localhost:5432` on the host.

## Production Deployment

When we move to production we will replace the dev manifest with the dedicated Helm chart
`deploy/helm/postgres-infra/` (coming in Sprint 4).  This chart will support:

1. Multi-AZ replication with Patroni or Stolon
2. Automated backups to object storage
3. Monitoring via `postgres_exporter`
4. Optional TimescaleDB/pgvector extensions

## Connection String Example

```bash
export DATABASE_URL="postgresql://loom:loom@localhost:5432/loom"
```

In Python services, you can inject the URL via environment variables and access it using
Pydantic settings:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://loom:loom@localhost:5432/loom"
    
    model_config = {
        "env_prefix": "LOOM_",
        "case_sensitive": False,
    }
```

## Schema Management

All migrations are managed with **Alembic**.  The standard workflow is:

```bash
alembic revision -m "add user table"
alembic upgrade head
```

A pre-commit hook will validate that migrations are reversible and idempotent.

## Reasons for Choosing Postgres

1. **Ubiquity** – Available everywhere and well understood by engineers.
2. **Extension Ecosystem** – We can add TimescaleDB, pgvector, PostGIS, etc. incrementally.
3. **Tooling** – Rich set of client libraries, ORMs, and managed services.
4. **Operational Simplicity** – Easier to run in Kubernetes compared to clustered TSDBs.

---

> **Next Steps**
>
> *Sprint 3* will introduce an abstraction layer (`storage` package) and the first migrations. 