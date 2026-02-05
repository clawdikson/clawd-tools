# HealthSparq Centralized Docker Architecture

## Status: APPROVED

## Overview

Centralized Docker configuration for all 22 HealthSparq scraper projects, using Docker Compose `include` directive for cross-platform compatibility. Each project maintains its own dated output folder while sharing common Docker infrastructure.

## Current State

- 1 project has Docker: `audiobee_aetna_better_health_of_oklahoma/`
- 22 healthsparq projects migrated to library pattern (no Docker)

---

## Final Architecture

```
scraping/
├── docker/
│   └── healthsparq/
│       ├── Dockerfile              # Shared base image (python:3.12-slim + Chrome)
│       ├── docker-entrypoint.sh    # Xvfb setup (conditional via HEADLESS env)
│       ├── docker-compose.base.yml # Template with ${PROJECT_SLUG} variables
│       ├── docker_run.py           # Python CLI wrapper (cross-platform)
│       ├── generate.py             # One-time generator for all projects
│       ├── .env.example            # Template with all documented variables
│       └── DOCKER.md               # Central documentation
│
├── healthsparq/                    # Library package (COPY'd into image)
├── core/                           # Core package (COPY'd into image)
│
├── audiobee_christus_health_plan/
│   ├── config.yaml
│   ├── mapper.py
│   ├── run.py
│   ├── docker-compose.yml          # Auto-generated thin wrapper (~10 lines)
│   ├── .env.example                # Auto-generated with all vars
│   ├── data/                       # Static reference data (optional mount)
│   └── 20260115/                   # Project-local output (volume mounted)
│       ├── raw/
│       │   ├── search_results/
│       │   └── provider_details/
│       └── processed/
│           └── providers.jsonl
```

---

## Key Decisions

| Area | Decision | Rationale |
|------|----------|-----------|
| **Cross-platform** | Docker Compose `include` | No symlinks, works on Windows/macOS/Linux |
| **Image registry** | Both local + registry | Local for dev, registry push for distributed workers |
| **Library install** | COPY healthsparq/ | Simple, image rebuilds on library changes acceptable |
| **Parallel runs** | Single project only | Keep wrapper simple, orchestration is separate concern |
| **Coordination** | Env vars (MACHINE_INDEX/COUNT) | Current Aetna pattern, proven for distributed scraping |
| **Secrets** | .env files | Simple, acceptable for current security requirements |
| **Headless mode** | Conditional via HEADLESS env | Default HEADLESS=false (Xvfb on), set true for headless |
| **Base image** | python:3.12-slim | Proven stable with Chrome, good size/compatibility balance |
| **Build cache** | requirements.txt first | Standard Docker layer caching pattern |
| **Health checks** | Log file check | No code changes needed, checks for recent log writes |
| **Logs** | Volume mount | Project-local ./logs folder, persists after container stop |
| **Resources** | Configurable via env | MEM_LIMIT, CPU_LIMIT, SHM_SIZE env vars with defaults |
| **Generation** | Auto-generate all | One-time script generates docker-compose.yml for all 22 projects |
| **Phase control** | Pass-through args | Wrapper passes all args to run.py inside container |
| **Lifecycle** | Basic up/down only | docker compose up/down, user handles edge cases |
| **Gitignore** | Update per-project | Add Docker patterns to each project's .gitignore |
| **Image naming** | healthsparq:{project} | e.g., healthsparq:christus - single repo with tags |
| **Static data** | Fallback pattern | COPY data/ into image, allow mount override at runtime |
| **Env template** | Full .env.example | Generate with all configurable vars documented |
| **Wrapper script** | Python (standalone) | Cross-platform, docker/healthsparq/docker_run.py |
| **Path mapping** | Exact match | /app/{date}/ maps to ./{date}/ - same structure |
| **Data cleanup** | No auto-cleanup | User manages manually, no accidental data loss |
| **Re-runnability** | One-time only | Generate once, projects own their docker-compose.yml |
| **Documentation** | Central only | Single DOCKER.md in docker/healthsparq/ |

---

## Technical Specification

### 1. Dockerfile (`docker/healthsparq/Dockerfile`)

```dockerfile
# Shared HealthSparq Docker image
# Build context: scraping/ (parent directory)
# Usage: docker build -t healthsparq -f docker/healthsparq/Dockerfile .

FROM --platform=linux/amd64 python:3.12-slim

# Install system dependencies for Chrome and Xvfb
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates \
    xvfb xauth \
    fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    libatspi2.0-0 libcups2 libdbus-1-3 libdrm2 libgbm1 libgtk-3-0 \
    libnspr4 libnss3 libxcomposite1 libxdamage1 libxfixes3 \
    libxkbcommon0 libxrandr2 \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first (layer caching)
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy core and healthsparq packages
COPY core/ ./core/
COPY healthsparq/ ./healthsparq/
RUN pip install --no-cache-dir -e ./healthsparq

# Copy project data (fallback, can be overridden via mount)
ARG PROJECT_SLUG
COPY ${PROJECT_SLUG}/data/ ./data/ 2>/dev/null || true

# Copy project files
COPY ${PROJECT_SLUG}/ ./project/

# Copy .env for proxy credentials
COPY .env* ./

# Create directories
RUN mkdir -p logs

# Environment
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
ENV HEADLESS=false

# Entrypoint handles Xvfb conditionally
COPY docker/healthsparq/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["python", "project/run.py", "run"]
```

### 2. Entrypoint (`docker/healthsparq/docker-entrypoint.sh`)

```bash
#!/bin/bash
set -e

# Conditional Xvfb based on HEADLESS env var
if [ "$HEADLESS" = "true" ]; then
    echo "Running in headless mode (no Xvfb)"
    export DISPLAY=
else
    echo "Starting Xvfb on display :99..."
    Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
    XVFB_PID=$!
    sleep 2

    if ! kill -0 $XVFB_PID 2>/dev/null; then
        echo "ERROR: Xvfb failed to start"
        exit 1
    fi
    echo "Xvfb started (PID: $XVFB_PID)"
    export DISPLAY=:99
fi

echo "Running: $@"
exec "$@"
```

### 3. Base Compose (`docker/healthsparq/docker-compose.base.yml`)

```yaml
version: "3.8"

services:
  scraper:
    build:
      context: ../..
      dockerfile: docker/healthsparq/Dockerfile
      args:
        PROJECT_SLUG: ${PROJECT_SLUG}
    image: healthsparq:${PROJECT_SLUG:-latest}
    container_name: healthsparq-${PROJECT_SLUG:-default}-${MACHINE_ID:-local}

    environment:
      # Project
      - SCRAPER_PROJECT_NAME=${PROJECT_SLUG}
      - SCRAPER_CURR_DATE=${SCRAPER_CURR_DATE:-20260115}

      # Workers
      - SCRAPER_NUM_WORKERS=${NUM_WORKERS:-3}
      - SCRAPER_WORKER_OFFSET=${WORKER_OFFSET:-0}
      - SCRAPER_MACHINE_ID=${MACHINE_ID:-local}

      # Distributed mode
      - SCRAPER_MACHINE_INDEX=${MACHINE_INDEX:-0}
      - SCRAPER_MACHINE_COUNT=${MACHINE_COUNT:-1}

      # Display
      - HEADLESS=${HEADLESS:-false}

      # Proxy credentials (from .env)
      - SMARTPROXY_USERNAME=${SMARTPROXY_USERNAME}
      - SMARTPROXY_PASSWORD=${SMARTPROXY_PASSWORD}
      - DATAIMPULSE_USERNAME=${DATAIMPULSE_USERNAME}
      - DATAIMPULSE_PASSWORD=${DATAIMPULSE_PASSWORD}

    volumes:
      # Output - project-local dated folder
      - ./${SCRAPER_CURR_DATE:-20260115}:/app/${SCRAPER_CURR_DATE:-20260115}
      # Logs
      - ./logs:/app/logs
      # Static data (optional override)
      - ./data:/app/data:ro

    shm_size: ${SHM_SIZE:-2gb}

    deploy:
      resources:
        limits:
          memory: ${MEM_LIMIT:-4G}
          cpus: "${CPU_LIMIT:-2}"
        reservations:
          memory: ${MEM_RESERVE:-2G}
          cpus: "${CPU_RESERVE:-1}"

    restart: unless-stopped

    healthcheck:
      test: ["CMD", "sh", "-c", "find /app/logs -mmin -5 -type f | grep -q ."]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 120s
```

### 4. Per-Project Compose (Auto-generated)

```yaml
# audiobee_christus_health_plan/docker-compose.yml
# Auto-generated - do not edit manually

include:
  - path: ../docker/healthsparq/docker-compose.base.yml

services:
  scraper:
    environment:
      - PROJECT_SLUG=audiobee_christus_health_plan
```

### 5. Python CLI Wrapper (`docker/healthsparq/docker_run.py`)

```python
#!/usr/bin/env python3
"""Cross-platform Docker CLI wrapper for HealthSparq scrapers."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def get_project_dir(project_slug: str) -> Path:
    """Get project directory path."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    project_dir = repo_root / project_slug

    if not project_dir.exists():
        print(f"Error: Project directory not found: {project_dir}")
        sys.exit(1)

    return project_dir


def run_compose(project_dir: Path, action: str, extra_args: list[str]) -> int:
    """Run docker compose command in project directory."""
    cmd = ["docker", "compose", action] + extra_args

    print(f"Running: {' '.join(cmd)}")
    print(f"Directory: {project_dir}")

    result = subprocess.run(cmd, cwd=project_dir)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="HealthSparq Docker Runner")
    parser.add_argument("project", help="Project slug (e.g., audiobee_christus_health_plan)")
    parser.add_argument("action", choices=["up", "down", "build", "logs"],
                       help="Docker compose action")
    parser.add_argument("--curr", help="Current date (YYYYMMDD)")
    parser.add_argument("--detach", "-d", action="store_true", help="Run in background")
    parser.add_argument("--build", action="store_true", help="Rebuild image before up")
    parser.add_argument("extra", nargs="*", help="Extra arguments passed to run.py")

    args = parser.parse_args()

    project_dir = get_project_dir(args.project)

    # Set environment variables
    env = os.environ.copy()
    env["PROJECT_SLUG"] = args.project
    if args.curr:
        env["SCRAPER_CURR_DATE"] = args.curr

    os.environ.update(env)

    # Build extra args
    extra_args = []
    if args.action == "up":
        if args.detach:
            extra_args.append("-d")
        if args.build:
            extra_args.append("--build")

    # Pass extra args to container command
    if args.extra and args.action == "up":
        # Override CMD with extra args
        extra_args.extend(["--", "python", "project/run.py", "run"] + args.extra)

    return run_compose(project_dir, args.action, extra_args)


if __name__ == "__main__":
    sys.exit(main())
```

### 6. Generator Script (`docker/healthsparq/generate.py`)

```python
#!/usr/bin/env python3
"""One-time generator for per-project Docker files."""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent

DOCKER_COMPOSE_TEMPLATE = '''# {project_slug}/docker-compose.yml
# Auto-generated by docker/healthsparq/generate.py

include:
  - path: ../docker/healthsparq/docker-compose.base.yml

services:
  scraper:
    environment:
      - PROJECT_SLUG={project_slug}
'''

ENV_EXAMPLE_TEMPLATE = '''# {project_slug}/.env.example
# Docker configuration for {project_slug}

# Required
SCRAPER_CURR_DATE=20260115
PROJECT_SLUG={project_slug}

# Proxy credentials
SMARTPROXY_USERNAME=
SMARTPROXY_PASSWORD=
DATAIMPULSE_USERNAME=
DATAIMPULSE_PASSWORD=

# Worker configuration
NUM_WORKERS=3
WORKER_OFFSET=0
MACHINE_ID=local

# Distributed mode (for multi-machine runs)
MACHINE_INDEX=0
MACHINE_COUNT=1

# Display mode (false=Xvfb for anti-bot, true=headless)
HEADLESS=false

# Resource limits (optional)
MEM_LIMIT=4G
CPU_LIMIT=2
SHM_SIZE=2gb
MEM_RESERVE=2G
CPU_RESERVE=1
'''

GITIGNORE_ADDITIONS = '''
# Docker
.env
docker-compose.override.yml
'''


def get_healthsparq_projects() -> list[str]:
    """Find all healthsparq projects."""
    projects = []
    for item in REPO_ROOT.iterdir():
        if item.is_dir() and item.name.startswith("audiobee_"):
            config_yaml = item / "config.yaml"
            if config_yaml.exists():
                content = config_yaml.read_text()
                if "site_type: healthsparq" in content or "healthsparq" in item.name:
                    projects.append(item.name)
    return sorted(projects)


def generate_for_project(project_slug: str) -> None:
    """Generate Docker files for a single project."""
    project_dir = REPO_ROOT / project_slug

    # Generate docker-compose.yml
    compose_file = project_dir / "docker-compose.yml"
    compose_file.write_text(DOCKER_COMPOSE_TEMPLATE.format(project_slug=project_slug))
    print(f"  Created: {compose_file}")

    # Generate .env.example
    env_example = project_dir / ".env.example"
    env_example.write_text(ENV_EXAMPLE_TEMPLATE.format(project_slug=project_slug))
    print(f"  Created: {env_example}")

    # Update .gitignore
    gitignore = project_dir / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text()
        if "# Docker" not in content:
            gitignore.write_text(content + GITIGNORE_ADDITIONS)
            print(f"  Updated: {gitignore}")
    else:
        gitignore.write_text(GITIGNORE_ADDITIONS.strip() + "\n")
        print(f"  Created: {gitignore}")


def main():
    print("HealthSparq Docker Generator")
    print("=" * 40)

    projects = get_healthsparq_projects()
    print(f"\nFound {len(projects)} healthsparq projects\n")

    for project in projects:
        print(f"Generating for {project}:")
        generate_for_project(project)
        print()

    print(f"Done! Generated Docker files for {len(projects)} projects.")


if __name__ == "__main__":
    main()
```

### 7. Environment Template (`docker/healthsparq/.env.example`)

```bash
# HealthSparq Docker Environment Variables
# Copy to project directory as .env and fill in values

# === REQUIRED ===
SCRAPER_CURR_DATE=20260115
PROJECT_SLUG=audiobee_project_name

# === PROXY CREDENTIALS ===
SMARTPROXY_USERNAME=your_username
SMARTPROXY_PASSWORD=your_password
DATAIMPULSE_USERNAME=your_username
DATAIMPULSE_PASSWORD=your_password

# === WORKER CONFIGURATION ===
NUM_WORKERS=3              # Number of browser workers
WORKER_OFFSET=0            # Starting worker ID (for unique proxy sessions)
MACHINE_ID=local           # Identifier for this machine

# === DISTRIBUTED MODE ===
# For running across multiple machines
MACHINE_INDEX=0            # This machine's index (0-based)
MACHINE_COUNT=1            # Total number of machines

# === DISPLAY MODE ===
HEADLESS=false             # false=Xvfb (anti-bot), true=headless

# === RESOURCE LIMITS (optional) ===
MEM_LIMIT=4G               # Container memory limit
CPU_LIMIT=2                # Container CPU limit
SHM_SIZE=2gb               # Shared memory for Chrome
MEM_RESERVE=2G             # Memory reservation
CPU_RESERVE=1              # CPU reservation
```

---

## Usage Examples

### Basic Usage

```bash
# From project directory
cd audiobee_christus_health_plan
cp .env.example .env
# Edit .env with proxy credentials

# Build and run
docker compose up --build

# Run in background
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Using Python Wrapper (Cross-platform)

```bash
# Run scraper
python docker/healthsparq/docker_run.py audiobee_christus_health_plan up --curr 20260115

# Run with extra args (passed to run.py)
python docker/healthsparq/docker_run.py audiobee_christus_health_plan up --curr 20260115 --phase 1-3

# Build only
python docker/healthsparq/docker_run.py audiobee_christus_health_plan build

# View logs
python docker/healthsparq/docker_run.py audiobee_christus_health_plan logs
```

### Distributed Scraping

```bash
# Machine 1
MACHINE_ID=srv1 WORKER_OFFSET=0 NUM_WORKERS=5 MACHINE_INDEX=0 MACHINE_COUNT=3 docker compose up -d

# Machine 2
MACHINE_ID=srv2 WORKER_OFFSET=5 NUM_WORKERS=5 MACHINE_INDEX=1 MACHINE_COUNT=3 docker compose up -d

# Machine 3
MACHINE_ID=srv3 WORKER_OFFSET=10 NUM_WORKERS=5 MACHINE_INDEX=2 MACHINE_COUNT=3 docker compose up -d
```

### Registry Push

```bash
# Build with tag
docker build -t healthsparq:christus -f docker/healthsparq/Dockerfile --build-arg PROJECT_SLUG=audiobee_christus_health_plan .

# Tag for registry
docker tag healthsparq:christus your-registry.com/healthsparq:christus

# Push
docker push your-registry.com/healthsparq:christus
```

---

## Implementation Steps

1. [ ] Create `docker/healthsparq/` directory structure
2. [ ] Write Dockerfile (shared base image)
3. [ ] Write docker-entrypoint.sh (conditional Xvfb)
4. [ ] Write docker-compose.base.yml (template)
5. [ ] Write docker_run.py (Python CLI wrapper)
6. [ ] Write generate.py (one-time generator)
7. [ ] Write .env.example (template)
8. [ ] Write DOCKER.md (documentation)
9. [ ] Run generate.py to create per-project files
10. [ ] Test with one project (audiobee_christus_health_plan)
11. [ ] Verify cross-platform (macOS, Linux, Windows/WSL2)

---

## Files to Create

| File | Lines | Purpose |
|------|-------|---------|
| `docker/healthsparq/Dockerfile` | ~60 | Shared base image |
| `docker/healthsparq/docker-entrypoint.sh` | ~25 | Conditional Xvfb |
| `docker/healthsparq/docker-compose.base.yml` | ~70 | Template with variables |
| `docker/healthsparq/docker_run.py` | ~80 | Python CLI wrapper |
| `docker/healthsparq/generate.py` | ~100 | One-time generator |
| `docker/healthsparq/.env.example` | ~30 | Environment template |
| `docker/healthsparq/DOCKER.md` | ~200 | Central documentation |
| Per-project `docker-compose.yml` | ~10 each | Auto-generated thin wrappers |
| Per-project `.env.example` | ~25 each | Auto-generated env templates |
