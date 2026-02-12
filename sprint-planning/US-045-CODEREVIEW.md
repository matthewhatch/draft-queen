# US-045 Code Review: Dockerize Application for Production Deployment

**Reviewer:** GitHub Copilot  
**Date:** February 12, 2026  
**Sprint:** Sprint 4  
**Scope:** 7 new files, 1 modified file

---

## Scope of Changes

| File | Status |
|---|---|
| `docker/Dockerfile.api` | New |
| `docker/Dockerfile.pipeline` | New |
| `docker/init-db.sh` | New |
| `docker/.dockerignore` | New |
| `docker-compose.yml` | New |
| `.env.example` | Modified |
| `docs/DOCKER_SETUP.md` | New |
| `docs/US-045_COMPLETION_REPORT.md` | New |
| `docs/US-045_IMPLEMENTATION_PLAN.md` | New |
| `docs/US-045_SUMMARY.md` | New |

---

## 🔴 Critical Issues (4) — Will prevent the stack from working

### 1. Wrong uvicorn import path — API won't start

**Files:** `docker/Dockerfile.api` (line 64), `docker-compose.yml` (line 80)

Both the Dockerfile CMD and the compose command reference `backend.api.routes:app`, but there is no `app` (FastAPI instance) defined in that module — it only contains `APIRouter` instances. The actual FastAPI `app` object lives in the top-level `main.py`. The correct target is `main:app`.

```dockerfile
# Current (broken)
CMD ["uvicorn", "backend.api.routes:app", ...]
command: uvicorn backend.api.routes:app --host 0.0.0.0 --port 8000 --reload

# Should be
CMD ["uvicorn", "main:app", ...]
command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

### 2. Environment variable names don't match `config.py`

**File:** `docker-compose.yml` (lines 53–58, 90–95)

The application's `Settings` class (pydantic-settings) expects `DB_USERNAME` and `DB_DATABASE`, but docker-compose passes `DB_USER` and `DB_NAME`. The app will silently fall back to defaults (`postgres` / `nfl_draft`) instead of the intended values, causing a wrong database connection.

| What the app expects | What compose sets | Match? |
|---|---|---|
| `DB_USERNAME` | `DB_USER` | ❌ |
| `DB_DATABASE` | `DB_NAME` | ❌ |
| `DB_HOST` | `DB_HOST` | ✅ |
| `DB_PASSWORD` | `DB_PASSWORD` | ✅ |

---

### 3. `init-db.sh` missing execute permission

**File:** `docker/init-db.sh`

The file has mode `644` (no execute bit). PostgreSQL's `docker-entrypoint-initdb.d` mechanism requires `.sh` files to be executable. The init script will be **silently skipped**, so no extensions or alembic tables will be created.

**Fix:** `chmod +x docker/init-db.sh`

---

### 4. `json1` is a SQLite extension, not PostgreSQL

**File:** `docker/init-db.sh` (line 18)

```sql
CREATE EXTENSION IF NOT EXISTS "json1";
```

`json1` doesn't exist in PostgreSQL — it's a SQLite extension. Combined with `set -e` at the top of the script, this error will **abort the entire init script** before creating the schema, granting permissions, or creating the `alembic_version` table. PostgreSQL has built-in JSON/JSONB support; this line should be removed entirely.

---

## 🟠 High Issues (2)

### 5. `.dockerignore` is in the wrong location

**File:** `docker/.dockerignore`

Both Dockerfiles specify `context: .` (project root) in docker-compose. Docker only reads `.dockerignore` from the **build context root**, not from subdirectories. The file at `docker/.dockerignore` is completely ignored during builds. This means the entire repo (including the `env/` virtualenv, `__pycache__/`, `.git/`, test files, notebooks, etc.) gets sent as build context and copied into the image.

**Fix:** Move or copy this file to the project root as `.dockerignore`.

---

### 6. Pipeline restart loop

**File:** `docker-compose.yml` (line 110)

The pipeline service runs a one-shot script (`pff_pipeline_setup`) but has `restart: unless-stopped`. When the script completes (exit 0), Docker will immediately restart it, creating an infinite loop. 

**Fix:** Change to `restart: "no"` or `restart: on-failure`, or redesign the pipeline as an on-demand `docker compose run` command rather than a perpetually restarting service.

---

## 🟡 Medium / Low Issues (5)

### 7. `.env.example` formatting — comment smashed onto value

**File:** `.env.example` (line 74)

```
LOGGING_LOKI_URL=http://localhost:3100# App Configuration
```

A missing newline causes `# App Configuration` to be parsed as part of the URL value, resulting in a broken URL. Also introduces a duplicate `ENVIRONMENT=development` line (appears at both line 7 and the end of the file).

---

### 8. `poetry install --no-dev` is deprecated

**Files:** `docker/Dockerfile.api` (line 21), `docker/Dockerfile.pipeline` (line 21)

With Poetry 1.7.0, `--no-dev` has been deprecated since Poetry 1.2 (July 2022). The correct flag is `--without dev`. Builds will work today but emit deprecation warnings and may break on future Poetry versions.

```dockerfile
# Current (deprecated)
poetry install --no-dev --no-root

# Should be
poetry install --without dev --no-root
```

---

### 9. `version: '3.9'` in docker-compose.yml is obsolete

**File:** `docker-compose.yml` (line 1)

Docker Compose V2 ignores this field and emits a warning. It can be safely removed.

---

### 10. Missing planned deliverables

The implementation plan listed the following files to create, but none were delivered:

- `docker/entrypoint.api.sh`
- `docker/entrypoint.pipeline.sh`
- `docker-compose.prod.yml`

The entrypoint scripts were replaced by inline `command:` directives in compose (acceptable trade-off), but the production override file is only described as a code snippet in the docs, not as an actual file.

---

### 11. No health check on the pipeline container

The API container has a `HEALTHCHECK` directive, but the pipeline container has none. While it doesn't serve HTTP, a health check (e.g., checking process presence or a heartbeat file) would help detect stuck pipelines.

---

## ✅ What's Done Well

- **Multi-stage builds** — Clean separation of builder and runtime stages keeps image size down.
- **Non-root user** (`appuser`) — Good security posture in both Dockerfiles.
- **Layer ordering** — Dependencies installed before app code, maximizing Docker layer cache hits.
- **Health checks** on DB and Redis services with proper `depends_on: condition: service_healthy`.
- **pgAdmin behind a dev profile** — Prevents accidental exposure in production.
- **Named volumes** for data persistence — properly defined and scoped.
- **`PYTHONUNBUFFERED=1`** and **`PYTHONDONTWRITEBYTECODE=1`** — Correct container Python settings.
- **Playwright system dependencies** included in the pipeline Dockerfile.
- **Comprehensive documentation** — The 500+ line DOCKER_SETUP.md is thorough with architecture diagrams, common commands, troubleshooting, and production guidance.

---

## Summary

| Severity | Count | Issues |
|---|---|---|
| 🔴 Critical | 4 | Wrong uvicorn path, env var mismatch, init-db.sh not executable, `json1` not a PG extension |
| 🟠 High | 2 | `.dockerignore` in wrong location, pipeline restart loop |
| 🟡 Medium/Low | 5 | `.env.example` formatting, deprecated `--no-dev`, obsolete `version`, missing deliverables, no pipeline healthcheck |

**Verdict:** The architecture and approach are solid, but the **4 critical bugs will prevent the stack from starting correctly**. These must be fixed before merging. The high and medium issues should also be addressed but are lower risk.
