## Cursor Project Rules

### General Principles
- Follow the event-driven micro-services architecture described in `project.md`.
- Each processing unit is an **independent Python service** (container) consuming from **one or more Kafka topics** and producing to downstream topics.
- Prefer **async / await** & **FastAPI** for all network-bound code.
- Every service MUST be fully stateless except for Redis usage explicitly noted below.
- Dockerise every service; Helm charts live under `/deploy/charts/<service>`.
- All pre-trained model weights (HF safetensors, ONNX, etc.) are stored under the repo-level `models/` directory and mounted read-only into containers at `/models`.

### Topic Naming
Use the canonical pattern `<category>.<source>.<datatype>.<stage>` (all lowercase, dot-separated). Never invent new prefixes; extend existing hierarchies.

Examples:
- `device.sensor.gps.raw`
- `media.text.transcribed.words`

### Kafka Contracts
- **Key:** `device_id` when events originate from a single device, otherwise `null`.
- **Value:** JSON schema versioned with `schema_version` field.
- **Compression:** `lz4` for high-volume topics.

### Repository Layout
```
services/
  ingestion-api/    # FastAPI app – REST & WS
  consumers/
    vad/            # Silero VAD
    parakeet/       # Transcription
    moondream/
    ...
shared/
  proto_schemas/    # pydantic models & avro if needed
  util/
+models/            # Downloaded/converted model weights (git-ignored, mounted RO)
```

### Coding Style
- Black + Ruff enforced (PEP8 compliant).
- Use **pydantic v2** for all DTOs.
- No framework-level global state – dependency-inject with **FastAPI Depends** or `lagoon`.
- Unit tests with `pytest-asyncio`; minimum 80% coverage gate.

### Redis Usage
Only the following short-lived keys are allowed:
- `pair:<device_id>:<timestamp>` – buffering paired camera frames (TTL ≤ 30 s).
- `chunk:<file_id>:offset` – mapping audio/video chunks (TTL ≤ 5 min).

### TimescaleDB Schema
- Each logical event family has its own hypertable (`gps_data`, `transcripts`, etc.).
- Primary key `(time, device_id, <natural_key>)`.
- Partition interval: 1 day.

### Trino Integration
- All analytical SQL lives in `/sql/` and is tested via `pytest-sql`.

### Observability
- Emit OpenTelemetry traces to `otel-collector`.
- Metrics via Prometheus client – prefix with service name.

### CI / CD
- GitHub Actions → build & push multi-arch Docker images.
- FluxCD syncs `kustomize` overlays per environment: `dev`, `edge`, `prod`.

### Security
- Secrets injected via sealed-secrets; **never** committed in plain-text.
- All external HTTP calls must time-out within 5 s and have retry (max 2).

### Lint Rules (Cursor)
- Warn if a service consumes a topic but does **not** produce any output.
- Error if a topic string literal violates naming convention regex `^[a-z]+(\.[a-z0-9_]+)+$`.
- Warn if Redis TTL > allowed limits above.

### Style Guide
- Follow **Black** (line length 88) for formatting; enforced via pre-commit.
- **Ruff** ruleset: `ruff --select ALL --ignore ANN101,ANN102,E501,B905`.
- Docstrings: use **NumPy** style with type annotations; required for all public functions/classes.
- Commit messages: Conventional Commits (`feat:`, `fix:`, `chore:`) + scope (`service/vad`), body ≤ 72 chars per line.

### Python Dependency Management (uv)
- Each service contains a `pyproject.toml` managed by **uv**.
- Use command `uv pip sync -r requirements-locked.txt` inside Dockerfiles.
- Lock file: `requirements-locked.txt` committed and updated via CI on dependency bumps.
- No virtualenvs committed; devs run `uv venv .venv && uv pip install -r requirements-locked.txt`.

### Helm Chart Standards
- Charts live under `deploy/charts/<service>`; one chart per micro-service.
- `Chart.yaml` must include: `appVersion`, `kubeVersion`, semantic `version`.
- Kubernetes objects must contain labels:
  - `app.kubernetes.io/name`
  - `app.kubernetes.io/instance`
  - `app.kubernetes.io/version`
  - `app.kubernetes.io/component` (e.g., consumer, ingestion-api)
  - `app.kubernetes.io/part-of=loom`
- All images referenced via digest, **not** mutable tags.
- Resources: define requests and limits; CPU in millicores, memory in MiB.
- Health probes: `livenessProbe` on `/healthz`, `readinessProbe` on `/readyz`.
- Config via `values.yaml`; no hard-coded env vars in templates.

### Flux GitOps Migrations
- Environment overlays under `deploy/flux/overlays/{dev,edge,prod}` using **kustomize**.
- Promote via pull request merging into `main`; Flux watches `main`.
- Each overlay patches only values that differ from base; avoid duplication.
- Migration steps (DB schema etc.) handled via Helm `postUpgrade` hooks or separate `job` manifests.

### Extended Folder Structure
```
loomv2/
  services/
    <service-name>/
      app/                 # Python source
      pyproject.toml
      requirements-locked.txt
      Dockerfile
      charts/              # Optional, thin wrapper chart if not using top-level
  deploy/
    charts/                # Helm charts (source of truth)
    flux/
      base/                # kustomization.yaml + common patches
      overlays/
        dev/
        edge/
        prod/
  models/           # Central cache of model files
  tests/
    unit/
    integration/
  sql/
  docs/
```

### Testing Requirements
- **Unit tests**: `pytest -q`; cover business logic with ≥ 80% coverage.
- **Integration tests**: use **testcontainers** to spin up Kafka, Redis, TimescaleDB.
- CI matrix runs unit tests on `ubuntu-latest` **and** `macos-latest` to mimic dev environments.
- For consumer services, include contract tests verifying produced messages against JSON schema.
- Use `pytest-mock` for patching external calls; network access blocked by default.

### Makefile Targets (recommended)
- `make test` – unit + integration tests
- `make lint` – black + ruff
- `make docker` – build local image via BuildKit
- `make helm` – lint chart with `helm lint` & `helm template` dry-run

### Versioning & Releases
- Each service independently versioned via Git tag (`service/vad/v1.2.3`).
- CI publishes image `ghcr.io/<org>/<service>:vX.Y.Z` and updates Helm `appVersion` automatically.

### Quality Gates
- PR cannot merge unless:
  - All Make targets succeed.
  - Coverage ≥ threshold.
  - Helm template renders without error for all overlays.
  - Flux `kustomize build` passes `kubeval` validation.

### Development Workflow
**Commit Early & Often:**
- Commit after **every logical unit of work** (single function, test, config change).
- Never commit broken code; each commit should be deployable.
- Use atomic commits: one concept per commit (don't mix refactoring + new features).

**Before Every Commit:**
1. **Run tests:** `pytest tests/unit/` for the service you're changing.
2. **Pre-commit hooks:** Will auto-run on `git commit` (lint, format, test).
3. **Manual verification:** Start the service locally if touching core logic.

**Commit Message Format:**
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```
Examples:
- `feat(ingestion-api): add /audio endpoint with chunking`
- `fix(vad): handle empty audio frames gracefully` 
- `chore(helm): bump kafka chart to v0.21.2`

**Branch Strategy:**
- **Main branch:** Always deployable to production.
- **Feature branches:** `feat/<service>-<description>` (e.g., `feat/vad-silero-integration`).
- **Hotfix branches:** `fix/<issue-id>-<description>`.
- Delete feature branches after merge.

**Pull Request Process:**
1. **Self-review:** Walk through your own diff before requesting review.
2. **Tests pass:** CI must be green before requesting review.
3. **Small PRs:** Target <400 lines changed; split large features.
4. **Documentation:** Update relevant docs in the same PR.

**Local Development Loop:**
```bash
# 1. Make changes
vim services/vad/app/main.py

# 2. Test changes
make test

# 3. Commit atomically  
git add services/vad/app/main.py
git commit -m "feat(vad): add silence detection threshold"

# 4. Push frequently
git push origin feat/vad-silence-detection

# 5. Open PR when feature complete
gh pr create --title "VAD: Add configurable silence detection"
```

**Integration Testing:**
- After merging to `main`, verify in `dev` environment.
- **Kafka lag monitoring:** Check consumer lag stays <1000 messages.
- **TimescaleDB queries:** Verify new data is being ingested correctly.

**Rollback Strategy:**
- Each service tagged independently: `git tag service/vad/v1.2.3`.
- Helm can rollback individual services: `helm rollback vad-consumer 2`.
- Keep last 3 working versions deployed for instant rollback.

---
These rules are authoritative for automated audits and code reviews in this repo. 