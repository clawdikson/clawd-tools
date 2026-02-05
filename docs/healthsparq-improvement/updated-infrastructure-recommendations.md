# Updated Infrastructure Recommendations

> **Revised scaling strategy incorporating healthsparq-server deprecation**

---

## Summary

The deprecation of healthsparq-server significantly simplifies the infrastructure and improves the viability of the existing PLAN.md scaling approach. This document updates the recommendations based on the new architecture.

---

## Impact of Healthsparq-Server Deprecation

### Before: Two-Process Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OLD: HEALTHSPARQ EXECUTION                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Terminal 1 (must stay open):                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  cd healthsparq-server && PORT=1018 npm start               │   │
│  │  [Node.js server consuming 200-300MB RAM]                   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                               │                                     │
│                               │ HTTP (localhost:1018)               │
│                               ▼                                     │
│  Terminal 2:                                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  cd audiobee_<carrier> && python3 run_all.py                │   │
│  │  [Python scraper]                                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Issues:                                                            │
│  • Two processes to manage                                          │
│  • Server must be started before scraper                            │
│  • Port conflicts when running multiple scrapers                   │
│  • Node.js dependency in Python-focused infrastructure             │
│  • Complex error handling across process boundary                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### After: Single-Process Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    NEW: HEALTHSPARQ EXECUTION                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Single Terminal:                                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  cd audiobee_<carrier> && python3 run_all.py                │   │
│  │  [Self-contained Python process]                            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Benefits:                                                          │
│  • Single process to manage                                         │
│  • No server startup required                                       │
│  • No port conflicts                                                │
│  • Pure Python stack                                                │
│  • 10x faster API calls (50-100ms vs 500-1000ms)                   │
│  • 3x lower memory (50-100MB vs 200-300MB)                         │
│  • Native async error handling                                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Updated Scaling Strategy

The existing PLAN.md approach becomes **even more viable** with the new architecture:

### PLAN.md Approach (Revised)

```
┌─────────────────────────────────────────────────────────────────────┐
│                 SIMPLE PARALLEL EXECUTION (REVISED)                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  LOCAL TIER (3 Windows PCs)                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                             │   │
│  │  PC1 (8 cores)         PC2 (8 cores)         PC3 (8 cores) │   │
│  │  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐ │   │
│  │  │ 8 scrapers  │      │ 8 scrapers  │      │ 8 scrapers  │ │   │
│  │  │ in parallel │      │ in parallel │      │ in parallel │ │   │
│  │  └─────────────┘      └─────────────┘      └─────────────┘ │   │
│  │                                                             │   │
│  │  Total: 24 scrapers running simultaneously                  │   │
│  │  (Previously limited by healthsparq-server port conflicts)  │   │
│  │                                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  CLOUD TIER (AWS EC2 On-Demand)                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                             │   │
│  │  Burst instances for overflow                               │   │
│  │  ┌─────────────┐                                           │   │
│  │  │ t3.xlarge   │  No Node.js required!                     │   │
│  │  │ 4 cores     │  Simpler AMI (Python only)                │   │
│  │  │ 8 scrapers  │  Faster startup                           │   │
│  │  └─────────────┘                                           │   │
│  │                                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Improvements

| Aspect | Before (with healthsparq-server) | After (embedded) |
|--------|----------------------------------|------------------|
| **Local parallelism** | Limited by port conflicts | Unlimited |
| **Memory per Healthsparq** | 200-300MB server + scraper | 50-100MB total |
| **Scrapers per PC** | ~4-6 Healthsparq (port limits) | ~8-10 Healthsparq |
| **EC2 AMI** | Python + Node.js | Python only |
| **EC2 startup time** | ~60s (npm install) | ~30s |
| **Deployment complexity** | 2 runtimes | 1 runtime |

---

## Revised Project Assignment

### projects/pc1.txt (32 projects)

```
# API-based (Carrier, Sapphire, Anthem) - 20 projects
audiobee_florida_blue
audiobee_multiplan
audiobee_bcbs_ma
audiobee_harvard_pilgrim
audiobee_emblem
audiobee_bcbs_il
audiobee_molina
audiobee_carefirst
audiobee_anthem
audiobee_amerigroup
audiobee_healthy_blue
audiobee_simply_healthcare
audiobee_uhc_medicaid
audiobee_uhc_individual
audiobee_bcbs_kc
audiobee_bcbs_la
audiobee_bcbs_mn
audiobee_bcbs_mt
audiobee_bcbs_ne
audiobee_bcbs_nm

# Healthsparq v2 - 12 projects (no longer port-limited!)
audiobee_mvp_health
audiobee_medica
audiobee_medica_sg
audiobee_excellus
audiobee_ibx
audiobee_tufts_health_plans
audiobee_quartz
audiobee_alliance_trilogy
audiobee_highmark_wholecare
audiobee_capital_blue
audiobee_wellmark
audiobee_wellmark_medicare
```

### projects/pc2.txt (32 projects)

```
# API-based - 20 projects
audiobee_bcbs_sc_medicaid
audiobee_bcbs_tx
audiobee_braven_health
audiobee_cox_health_plans
audiobee_instil_health
audiobee_st_lukes
audiobee_baylor_scott_white
audiobee_blueshield_ca
audiobee_champion_health
audiobee_community_care_ca
audiobee_delaware_first
audiobee_firstcare_health
audiobee_fl_community_care
audiobee_gateway_health
audiobee_healthy_mississippi
audiobee_kelseycare
audiobee_la_care_health
audiobee_my_choice_wi
audiobee_nc_medicaid
audiobee_nextblue_nd

# Healthsparq v2 - 12 projects
audiobee_amerihealth_administrators_pa
audiobee_amerihealth_caritas_vip_de
audiobee_amerihealth_nj
audiobee_asuris_northwest
audiobee_christus_health_plan
audiobee_health_plan_nv_medicaid
audiobee_hma
audiobee_maine_community_health_options
audiobee_mass_gen
audiobee_medical_mutual
audiobee_first_choice_sc
audiobee_sentara
```

### projects/pc3.txt (31 projects)

```
# API-based - 29 projects
audiobee_northwell_direct
audiobee_or_health_share_medicaid
audiobee_partners_health_plan
audiobee_pehp
audiobee_qualcare
audiobee_qualchoice
audiobee_scan_health
audiobee_security_health_plan
audiobee_ucla_health
audiobee_upmc
audiobee_vermont_blue_advantage
audiobee_wellcare
audiobee_wyoblue_advantage
audiobee_aetna_better_health_of_oklahoma
audiobee_banner_health_medicare
audiobee_innovation_health
audiobee_jefferson_health
audiobee_physicians_health_plan_mi
audiobee_elderplan
# ... (remaining Carrier/Sapphire projects)

# No Healthsparq on PC3 - reserved for heavier scrapers
```

---

## Updated run.py

```python
#!/usr/bin/env python3
"""
Parallel scraper execution for local PCs.
Updated for healthsparq-server deprecation.
"""

import os
import sys
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# Configuration
SCRAPING_ROOT = Path("/Users/dikson/Work/ideon_scraping/scraping")
MAX_PARALLEL = int(os.environ.get("MAX_PARALLEL", "8"))

def run_scraper(project_name: str) -> tuple[str, bool, str]:
    """Run a single scraper project."""
    project_dir = SCRAPING_ROOT / project_name
    
    if not project_dir.exists():
        return project_name, False, f"Directory not found: {project_dir}"
    
    # No healthsparq-server startup needed!
    # All projects are now self-contained.
    
    try:
        result = subprocess.run(
            [sys.executable, "run_all.py"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=14400  # 4 hours max
        )
        
        if result.returncode == 0:
            return project_name, True, "Success"
        else:
            return project_name, False, result.stderr[-500:]
            
    except subprocess.TimeoutExpired:
        return project_name, False, "Timeout (4 hours)"
    except Exception as e:
        return project_name, False, str(e)

def main():
    # Load project list
    pc_name = os.environ.get("PC_NAME", "pc1")
    projects_file = SCRAPING_ROOT / "projects" / f"{pc_name}.txt"
    
    with open(projects_file) as f:
        projects = [
            line.strip() for line in f
            if line.strip() and not line.startswith("#")
        ]
    
    print(f"Running {len(projects)} projects with {MAX_PARALLEL} parallel workers")
    
    # Execute in parallel
    results = {"success": [], "failed": []}
    
    with ProcessPoolExecutor(max_workers=MAX_PARALLEL) as executor:
        futures = {
            executor.submit(run_scraper, project): project
            for project in projects
        }
        
        for future in as_completed(futures):
            project, success, message = future.result()
            
            if success:
                print(f"✅ {project}")
                results["success"].append(project)
            else:
                print(f"❌ {project}: {message}")
                results["failed"].append((project, message))
    
    # Summary
    print(f"\n{'='*50}")
    print(f"Success: {len(results['success'])}/{len(projects)}")
    print(f"Failed: {len(results['failed'])}/{len(projects)}")
    
    if results["failed"]:
        print("\nFailed projects:")
        for project, message in results["failed"]:
            print(f"  - {project}: {message[:100]}")

if __name__ == "__main__":
    main()
```

---

## Updated EC2 Deployment

### Simplified AMI (No Node.js)

```bash
#!/bin/bash
# ec2_setup.sh - Simplified for Python-only stack

# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Python 3.10+
sudo apt-get install -y python3.10 python3.10-venv python3-pip

# Dependencies
pip3 install patchright curl_cffi aiofiles orjson tenacity tqdm httpx

# Patchright browser
patchright install chromium

# Clone repository
git clone https://your-repo/ideon_scraping.git /opt/scraping

# NO NODE.JS REQUIRED!
# healthsparq-server is deprecated

echo "Setup complete"
```

### Faster Startup Script

```python
#!/usr/bin/env python3
# ec2_burst.py - Simplified burst execution

import boto3
import time

# Simpler user_data - no Node.js
USER_DATA = """#!/bin/bash
cd /opt/scraping

# Set proxy credentials
export SURFSHARK_USER="{surfshark_user}"
export SURFSHARK_PASS="{surfshark_pass}"

# Run assigned projects
export PC_NAME="ec2_burst"
python3 run.py

# Signal completion
aws sns publish --topic-arn {sns_topic} --message "EC2 burst complete"

# Self-terminate
sudo shutdown -h now
"""

def launch_burst(projects: list[str], surfshark_user: str, surfshark_pass: str):
    """Launch EC2 instance for burst execution."""
    ec2 = boto3.resource("ec2")
    
    # Write projects to file
    projects_content = "\n".join(projects)
    
    instance = ec2.create_instances(
        ImageId="ami-xxxxx",  # Your AMI
        InstanceType="t3.xlarge",
        MinCount=1,
        MaxCount=1,
        UserData=USER_DATA.format(
            surfshark_user=surfshark_user,
            surfshark_pass=surfshark_pass,
            sns_topic="arn:aws:sns:...",
        ),
        TagSpecifications=[{
            "ResourceType": "instance",
            "Tags": [{"Key": "Name", "Value": "scraper-burst"}]
        }]
    )[0]
    
    print(f"Launched instance: {instance.id}")
    return instance.id
```

---

## Memory & Performance Projections

### Per-PC Resource Usage

| Scenario | Healthsparq Scrapers | Memory Each | Total Memory |
|----------|---------------------|-------------|--------------|
| Old (v1) | 4 (port limited) | 300MB | 1.2GB |
| New (v2) | 10 (no limit) | 100MB | 1.0GB |

### Execution Time Improvements

| Phase | Old (v1) | New (v2) | Improvement |
|-------|----------|----------|-------------|
| Auth | 10-15s | 2-3s | 5x |
| Per API call | 500-1000ms | 50-100ms | 10x |
| 1000 providers | ~15 min | ~2 min | 7x |

### Overall Pipeline

For a typical Healthsparq project (10,000 providers):

| Phase | Old (v1) | New (v2) |
|-------|----------|----------|
| Phase 1 (Search) | 2-3 hours | 20-30 min |
| Phase 2 (Details) | 4-6 hours | 40-60 min |
| Phase 3 (Normalize) | 10-15 min | 10-15 min |
| **Total** | **6-9 hours** | **1.5-2 hours** |

---

## Recommendations Summary

### Immediate Actions

1. **Complete Healthsparq Migration (Weeks 1-6)**
   - Follow migration guide for all 24 projects
   - Validate output matches v1
   - Remove healthsparq-server dependency

2. **Update PLAN.md**
   - Remove healthsparq-server references
   - Update project assignments (no port limits)
   - Simplify EC2 AMI instructions

3. **Update Documentation**
   - docs/ARCHITECTURE.md
   - docs/SITE_TYPES_REFERENCE.md
   - docs/by-site-type/healthsparq.md
   - Individual CLAUDE.md files

### Medium-Term (Post-Migration)

1. **Increase Local Parallelism**
   - Test 10-12 scrapers per PC
   - Monitor memory usage
   - Optimize based on observed performance

2. **Simplify EC2 Deployment**
   - Create new AMI without Node.js
   - Test faster startup times
   - Update ec2_burst.py

3. **Consider SmartProxy Integration**
   - Surfshark proxies work well for current scale
   - SmartProxy residential may be needed for heavier anti-bot sites
   - Can be added incrementally per project

### Long-Term

1. **Unified Proxy Management**
   - Create SmartProxyManager class from previous proposal
   - Support multiple proxy providers
   - Automatic failover between providers

2. **Monitoring Dashboard**
   - Simple FastAPI dashboard
   - Track execution times, success rates
   - Alert on failures

3. **Consider Celery/Redis**
   - Only if scale exceeds 3 PCs + EC2 burst
   - Current simple approach handles ~100 projects well
   - Added complexity not justified yet

---

## Conclusion

The healthsparq-server deprecation is a significant improvement that:

1. **Simplifies deployment** - Pure Python stack, no Node.js
2. **Improves performance** - 7-10x faster for Healthsparq projects
3. **Enables more parallelism** - No port conflicts
4. **Reduces memory** - 3x lower per scraper
5. **Validates PLAN.md approach** - Simple parallel execution works even better now

The migration effort (6 weeks) is well worth the benefits. After migration, the existing PLAN.md scaling strategy should handle the ~100 project portfolio efficiently across 3 local PCs with occasional EC2 burst capacity.

---

*Last Updated: December 2024*
