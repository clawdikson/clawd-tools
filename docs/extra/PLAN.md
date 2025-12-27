# Ideon Scraping Infrastructure Scaling Plan

## Executive Summary

Scale from **95 to 190 scrapers** using:
1. **Parallel execution** on existing 3 Windows PCs (8-10x speedup)
2. **AWS EC2 burst** when local capacity is insufficient

**Philosophy**: Simple scripts, static configuration, cloud when needed.

---

## Architecture

```
LOCAL (Primary)                         CLOUD (Burst)
┌─────────────────────────────┐        ┌─────────────────────────────┐
│  PC-1        PC-2     PC-3  │        │  EC2 Fleet (On-Demand)      │
│  ┌───┐      ┌───┐    ┌───┐  │        │  ┌───┐ ┌───┐ ┌───┐ ┌───┐   │
│  │8  │      │8  │    │8  │  │   +    │  │5  │ │5  │ │5  │ │5  │   │
│  │API│      │API│    │API│  │        │  │API│ │API│ │API│ │API│   │
│  └───┘      └───┘    └───┘  │        │  └───┘ └───┘ └───┘ └───┘   │
│  30 parallel local          │        │  20+ parallel cloud         │
└─────────────────────────────┘        └─────────────────────────────┘
         │                                        │
         └────────────────┬───────────────────────┘
                          ▼
                    ┌───────────┐
                    │    S3     │
                    │  Output   │
                    └───────────┘
```

---

## Part 1: Local Parallel Execution

### 1.1 Environment Variable Support (One-Time Setup)

Update config.py files to accept dates via environment:

```python
import os

PREV_DATE = os.environ.get("PREV_DATE", "20251010")
CURR_DATE = os.environ.get("CURR_DATE", "20251110")
```

**Mass update script** (`tools/update_configs.py`):
```python
#!/usr/bin/env python3
"""Update all config.py files to use environment variables."""
import re
from pathlib import Path

def update_config(config_path: Path) -> bool:
    content = config_path.read_text()

    if 'os.environ.get("PREV_DATE"' in content:
        print(f"SKIP: {config_path}")
        return False

    # Backup first
    config_path.with_suffix('.py.bak').write_text(content)

    if "import os" not in content:
        content = "import os\n" + content

    content = re.sub(
        r'PREV_DATE\s*=\s*["\'](\d{8})["\']',
        r'PREV_DATE = os.environ.get("PREV_DATE", "\1")',
        content
    )
    content = re.sub(
        r'CURR_DATE\s*=\s*["\'](\d{8})["\']',
        r'CURR_DATE = os.environ.get("CURR_DATE", "\1")',
        content
    )

    config_path.write_text(content)
    print(f"UPDATED: {config_path}")
    return True

if __name__ == "__main__":
    updated = sum(1 for c in Path(".").glob("audiobee_*/config.py") if update_config(c))
    print(f"\nUpdated {updated} config files")
```

### 1.2 Parallel Runner

Simple script to run multiple scrapers in parallel:

```python
#!/usr/bin/env python3
"""
tools/run.py - Run scrapers in parallel.

Usage:
  python tools/run.py --projects pc1.txt --parallel 8 --curr 20251210 --prev 20251110
  python tools/run.py --pattern "audiobee_bcbs*" --parallel 8 --curr 20251210 --prev 20251110
"""
import os
import sys
import glob
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from tenacity import retry, stop_after_attempt, wait_exponential

# Resource limits (tested on 16GB PCs)
LIMITS = {"api": 8, "browser": 3, "antibot": 1}

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=30, max=120))
def run_scraper(project: str, curr: str, prev: str) -> tuple:
    """Run a single scraper with retry for transient failures."""
    start = datetime.now()
    project_path = Path(project)

    if not project_path.exists():
        return project, False, 0, f"Not found: {project}"

    env = os.environ.copy()
    env["CURR_DATE"] = curr
    env["PREV_DATE"] = prev
    env["PROJECT_NAME"] = project

    script = project_path / "run_all.py"
    if not script.exists():
        script = project_path / "index_1.py"

    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(project_path),
            env=env,
            capture_output=True,
            text=True,
            timeout=4 * 60 * 60  # 4 hour timeout
        )

        duration = (datetime.now() - start).total_seconds()

        if result.returncode == 0:
            return project, True, duration, None
        else:
            # Log full error to file
            log_dir = Path("logs") / curr
            log_dir.mkdir(parents=True, exist_ok=True)
            (log_dir / f"{project}.log").write_text(
                f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            )
            return project, False, duration, result.stderr[-200:] if result.stderr else "Unknown error"

    except subprocess.TimeoutExpired:
        return project, False, 14400, "Timeout (4h)"
    except Exception as e:
        return project, False, 0, str(e)

def main():
    parser = argparse.ArgumentParser(description="Run scrapers in parallel")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--projects", help="File with project names (one per line)")
    group.add_argument("--pattern", help="Glob pattern like 'audiobee_bcbs*'")
    parser.add_argument("--parallel", type=int, default=8, help="Parallel workers (default: 8)")
    parser.add_argument("--curr", required=True, help="Current date YYYYMMDD")
    parser.add_argument("--prev", required=True, help="Previous date YYYYMMDD")
    args = parser.parse_args()

    # Get project list
    if args.projects:
        projects = [p.strip() for p in Path(args.projects).read_text().splitlines() if p.strip()]
    else:
        projects = [d for d in glob.glob(args.pattern) if Path(d).is_dir()]

    if not projects:
        print("No projects found!")
        sys.exit(1)

    print(f"Running {len(projects)} projects with {args.parallel} workers")
    print(f"Dates: CURR={args.curr}, PREV={args.prev}\n")

    success, failed = 0, 0
    start_time = datetime.now()

    with ProcessPoolExecutor(max_workers=args.parallel) as executor:
        futures = {executor.submit(run_scraper, p, args.curr, args.prev): p for p in projects}

        for future in as_completed(futures):
            project, ok, duration, error = future.result()

            if ok:
                print(f"✓ {project} ({duration:.0f}s)")
                success += 1
            else:
                print(f"✗ {project} - {error}")
                failed += 1

    total_time = (datetime.now() - start_time).total_seconds()
    print(f"\n{'='*50}")
    print(f"Done in {total_time/60:.1f} minutes")
    print(f"Success: {success}/{len(projects)}, Failed: {failed}")

    if failed > 0:
        print(f"\nCheck logs/{args.curr}/ for error details")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### 1.3 Static Project Assignment

Split projects across PCs manually (simplest, most reliable):

**`projects/pc1.txt`** (~64 projects):
```
audiobee_bcbs_il
audiobee_bcbs_ma
audiobee_bcbs_la
...
```

**`projects/pc2.txt`** (~63 projects):
```
audiobee_florida_blue
audiobee_cigna
audiobee_multiplan
...
```

**`projects/pc3.txt`** (~63 projects):
```
audiobee_anthem
audiobee_humana
audiobee_uhc_medicaid
...
```

Generate these once:
```bash
ls -d audiobee_*/ | split -l 64 - projects/pc
mv projects/pcaa projects/pc1.txt
mv projects/pcab projects/pc2.txt
mv projects/pcac projects/pc3.txt
```

### 1.4 Running Locally

```bash
# On PC-1
python tools/run.py --projects projects/pc1.txt --parallel 8 --curr 20251210 --prev 20251110

# On PC-2
python tools/run.py --projects projects/pc2.txt --parallel 8 --curr 20251210 --prev 20251110

# On PC-3
python tools/run.py --projects projects/pc3.txt --parallel 8 --curr 20251210 --prev 20251110

# Or run specific patterns
python tools/run.py --pattern "audiobee_bcbs*" --parallel 8 --curr 20251210 --prev 20251110
```

### 1.5 Resource Limits

| PC RAM | API Scrapers | Browser Scrapers | Anti-bot |
|--------|-------------|------------------|----------|
| 8 GB | 5-6 | 2 | 1 |
| 16 GB | 8-10 | 3-4 | 1-2 |
| 32 GB | 15-20 | 6-8 | 2-3 |

**Browser scrapers**: Run with `--parallel 3` and ensure healthsparq-server is running.

---

## Part 2: AWS EC2 Burst Capacity

Use when local PCs can't handle the load (tight deadlines, 190+ projects).

### 2.1 EC2 Instance Types

| Scraper Type | Instance | vCPUs | RAM | Cost/hr | Parallel |
|--------------|----------|-------|-----|---------|----------|
| API | t3.medium | 2 | 4 GB | $0.042 | 5 |
| API (bulk) | t3.large | 2 | 8 GB | $0.083 | 10 |
| Browser | t3.xlarge | 4 | 16 GB | $0.166 | 3 |

### 2.2 EC2 Launcher

```python
#!/usr/bin/env python3
"""
tools/ec2_burst.py - Launch EC2 instances for burst capacity.

Usage:
  python tools/ec2_burst.py --projects overflow.txt --curr 20251210 --prev 20251110 --instances 5
"""
import os
import sys
import time
import boto3
import argparse
from pathlib import Path

# Configuration (set via environment or modify here)
CONFIG = {
    "ami_id": os.environ.get("SCRAPER_AMI_ID", "ami-xxxxxxxxx"),
    "instance_type": os.environ.get("SCRAPER_INSTANCE_TYPE", "t3.medium"),
    "key_name": os.environ.get("SCRAPER_KEY_NAME", "scraper-key"),
    "security_group": os.environ.get("SCRAPER_SG", "sg-xxxxxxxxx"),
    "subnet_id": os.environ.get("SCRAPER_SUBNET", "subnet-xxxxxxxxx"),
    "iam_role": os.environ.get("SCRAPER_IAM_ROLE", "scraper-ec2-role"),
    "s3_bucket": os.environ.get("SCRAPER_S3_BUCKET", "ideon-scraping-data"),
    "parallel_per_instance": 5,
    "max_instances": 10,  # Cost safety limit
}

USER_DATA_TEMPLATE = """#!/bin/bash
set -e

# Log everything
exec > >(tee /var/log/scraper.log) 2>&1

echo "Starting scraper at $(date)"
cd /opt/scraping

# Update code
git pull || echo "Git pull failed, using existing code"

# Activate environment
source venv/bin/activate

# Write project list
cat > /tmp/projects.txt << 'PROJECTS'
{projects}
PROJECTS

# Run scrapers
python tools/run.py \\
    --projects /tmp/projects.txt \\
    --parallel {parallel} \\
    --curr {curr} \\
    --prev {prev}

SCRAPER_EXIT=$?

# Sync results to S3 regardless of exit code
aws s3 sync /opt/scraping s3://{bucket}/runs/{curr}/ \\
    --exclude "*.py" --exclude "*.md" --exclude ".git/*" --exclude "venv/*"

echo "Completed at $(date) with exit code $SCRAPER_EXIT"

# Shutdown
sudo shutdown -h now
"""

def check_limits(ec2, count: int):
    """Prevent runaway costs."""
    response = ec2.describe_instances(
        Filters=[
            {"Name": "tag:Purpose", "Values": ["scraping-burst"]},
            {"Name": "instance-state-name", "Values": ["running", "pending"]}
        ]
    )
    running = sum(len(r["Instances"]) for r in response["Reservations"])

    if running + count > CONFIG["max_instances"]:
        raise RuntimeError(
            f"Cost limit: {running} running + {count} requested > {CONFIG['max_instances']} max. "
            f"Terminate existing instances or increase limit."
        )

def launch_instances(projects: list, curr: str, prev: str, count: int) -> list:
    """Launch EC2 instances to process projects."""
    ec2 = boto3.client("ec2")

    check_limits(ec2, count)

    # Split projects across instances
    chunk_size = len(projects) // count + 1
    chunks = [projects[i:i+chunk_size] for i in range(0, len(projects), chunk_size)]

    instance_ids = []

    for i, chunk in enumerate(chunks[:count]):
        user_data = USER_DATA_TEMPLATE.format(
            projects="\n".join(chunk),
            parallel=CONFIG["parallel_per_instance"],
            curr=curr,
            prev=prev,
            bucket=CONFIG["s3_bucket"]
        )

        response = ec2.run_instances(
            ImageId=CONFIG["ami_id"],
            InstanceType=CONFIG["instance_type"],
            KeyName=CONFIG["key_name"],
            SecurityGroupIds=[CONFIG["security_group"]],
            SubnetId=CONFIG["subnet_id"],
            IamInstanceProfile={"Name": CONFIG["iam_role"]},
            MinCount=1, MaxCount=1,
            UserData=user_data,
            InstanceInitiatedShutdownBehavior="terminate",
            TagSpecifications=[{
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "Name", "Value": f"scraper-burst-{i}"},
                    {"Key": "Purpose", "Value": "scraping-burst"},
                    {"Key": "CurrDate", "Value": curr},
                ]
            }]
        )

        instance_id = response["Instances"][0]["InstanceId"]
        instance_ids.append(instance_id)
        print(f"Launched {instance_id} with {len(chunk)} projects")

    return instance_ids

def monitor(instance_ids: list):
    """Monitor instances until completion."""
    ec2 = boto3.client("ec2")
    remaining = set(instance_ids)

    print(f"\nMonitoring {len(remaining)} instances (Ctrl+C to stop monitoring)...")

    try:
        while remaining:
            response = ec2.describe_instances(InstanceIds=list(remaining))

            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    state = instance["State"]["Name"]
                    iid = instance["InstanceId"]

                    if state == "terminated":
                        print(f"  {iid}: Completed")
                        remaining.discard(iid)
                    elif state == "running":
                        # Could add CloudWatch log checking here
                        pass

            if remaining:
                time.sleep(60)
                print(f"  Still running: {len(remaining)} instances...")

    except KeyboardInterrupt:
        print(f"\nStopped monitoring. {len(remaining)} instances still running.")
        print("They will auto-terminate when done.")

    print("\nAll instances completed" if not remaining else "")

def main():
    parser = argparse.ArgumentParser(description="Launch EC2 burst instances")
    parser.add_argument("--projects", required=True, help="Project list file")
    parser.add_argument("--curr", required=True, help="Current date YYYYMMDD")
    parser.add_argument("--prev", required=True, help="Previous date YYYYMMDD")
    parser.add_argument("--instances", type=int, default=1, help="Number of EC2 instances")
    parser.add_argument("--no-monitor", action="store_true", help="Don't wait for completion")
    args = parser.parse_args()

    projects = [p.strip() for p in Path(args.projects).read_text().splitlines() if p.strip()]

    if not projects:
        print("No projects in file!")
        sys.exit(1)

    print(f"Launching {args.instances} EC2 instances for {len(projects)} projects")
    print(f"Instance type: {CONFIG['instance_type']}")
    print(f"Estimated cost: ~${args.instances * 0.05 * 4:.2f} (4 hours)\n")

    instance_ids = launch_instances(projects, args.curr, args.prev, args.instances)

    if not args.no_monitor:
        monitor(instance_ids)

if __name__ == "__main__":
    main()
```

### 2.3 AMI Setup (One-Time)

Create a custom AMI with everything pre-installed:

```bash
#!/bin/bash
# Run on a fresh Amazon Linux 2 instance

# System packages
sudo yum update -y
sudo yum install -y git python3.9 python3.9-pip nodejs npm

# Clone repo
sudo mkdir -p /opt/scraping
sudo chown ec2-user:ec2-user /opt/scraping
cd /opt/scraping
git clone https://your-repo.git .

# Python environment
python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install tenacity boto3

# Node.js for healthsparq (if needed)
cd healthsparq-server && npm install && cd ..

# Chrome for browser scrapers
sudo amazon-linux-extras install -y epel
sudo yum install -y chromium

# Save as AMI from AWS Console, note the AMI ID
```

### 2.4 Running Burst

```bash
# Create overflow list (projects that didn't fit on local PCs)
cat projects/overflow.txt

# Launch 5 EC2 instances
python tools/ec2_burst.py \
    --projects projects/overflow.txt \
    --curr 20251210 \
    --prev 20251110 \
    --instances 5

# Or launch without monitoring
python tools/ec2_burst.py \
    --projects projects/overflow.txt \
    --curr 20251210 \
    --prev 20251110 \
    --instances 5 \
    --no-monitor
```

### 2.5 Cost Estimates

| Scenario | Instances | Hours | Cost |
|----------|-----------|-------|------|
| 50 API scrapers | 2 × t3.medium | 4h | ~$0.34 |
| 100 API scrapers | 4 × t3.medium | 4h | ~$0.67 |
| 30 browser scrapers | 3 × t3.xlarge | 6h | ~$3.00 |

**Monthly estimate** (2 bursts): ~$5-10/month

---

## Quick Reference

### Local Execution

```bash
# Run from project list
python tools/run.py --projects projects/pc1.txt --parallel 8 --curr 20251210 --prev 20251110

# Run by pattern
python tools/run.py --pattern "audiobee_bcbs*" --parallel 8 --curr 20251210 --prev 20251110

# Browser scrapers (lower parallelism)
python tools/run.py --projects projects/browser.txt --parallel 3 --curr 20251210 --prev 20251110
```

### Cloud Burst

```bash
# Launch EC2 instances
python tools/ec2_burst.py --projects projects/overflow.txt --curr 20251210 --prev 20251110 --instances 5
```

### One-Time Setup

```bash
# Update all config.py files (run once)
python tools/update_configs.py

# Generate project lists (run once)
ls -d audiobee_*/ | split -l 64 - projects/pc
```

---

## Files to Create

```
tools/
├── update_configs.py   # One-time config update
├── run.py              # Local parallel runner
└── ec2_burst.py        # Cloud burst launcher

projects/
├── pc1.txt             # Projects for PC-1 (~64)
├── pc2.txt             # Projects for PC-2 (~63)
├── pc3.txt             # Projects for PC-3 (~63)
├── browser.txt         # Browser-only projects
└── overflow.txt        # Projects for cloud burst
```

---

## Summary

| Before | After |
|--------|-------|
| 1 scraper at a time | 8-10 parallel per PC |
| ~48 hours for 95 scrapers | ~6-8 hours locally |
| No cloud option | EC2 burst for overflow |
| Complex job queues | Simple project lists |
| ~850 lines of code | ~250 lines of code |

**What was removed**:
- ❌ Network share job queue (static lists work)
- ❌ Smart resource detection (hardcoded limits)
- ❌ Distributed coordination (manual split)
- ❌ Elaborate result tracking (stdout + logs)

**What was kept**:
- ✅ Parallel execution (8-10x speedup)
- ✅ Environment variable support
- ✅ Retry logic for transient failures
- ✅ EC2 burst capacity
- ✅ Cost safety limits
- ✅ Error logging to files
