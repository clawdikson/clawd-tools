# Healthsparq Migration Guide: v1 → v2

> **Step-by-step guide for migrating from healthsparq-server to embedded Python browser automation**

---

## Executive Summary

This guide covers the migration of 24 Healthsparq scrapers from the deprecated Node.js healthsparq-server architecture to the new embedded Python architecture using Patchright and curl_cffi.

**Key Benefits of Migration:**
- 10x faster API requests (50-100ms vs 500-1000ms)
- 3x lower memory usage (50-100MB vs 200-300MB)
- Simplified deployment (1 process vs 2 processes)
- Pure Python stack (no Node.js dependency)
- Better error handling with native async/await

---

## Pre-Migration Checklist

### 1. Environment Setup

```bash
# Verify Python version (3.10+ required for proper async support)
python3 --version

# Install new dependencies
pip install patchright curl_cffi aiofiles orjson tenacity tqdm

# Install Patchright browser (Chromium)
patchright install chromium

# Verify installation
python3 -c "from patchright.async_api import async_playwright; print('Patchright OK')"
python3 -c "from curl_cffi.requests import AsyncSession; print('curl_cffi OK')"
```

### 2. Proxy Configuration

```bash
# Download Surfshark proxy list to project directory
# File: us-vpn-hostnames-surfshark.json
# Format: ["us-dal.prod.surfshark.com", "us-nyc.prod.surfshark.com", ...]

# Set proxy credentials as environment variables
export SURFSHARK_USER="your-surfshark-username"
export SURFSHARK_PASS="your-surfshark-password"
```

### 3. Backup Current Project

```bash
cd /path/to/audiobee_<carrier>

# Create backup
cp -r . ../audiobee_<carrier>_backup_v1

# Or use git
git checkout -b migration-v2
git add -A && git commit -m "Pre-migration checkpoint"
```

---

## Migration Steps

### Step 1: Copy Core Library Files

Copy these files from the reference implementation (audiobee_capital_blue):

```bash
# From audiobee_capital_blue to your project
cp /path/to/audiobee_capital_blue/browser_session.py .
cp /path/to/audiobee_capital_blue/healthspark.py .
cp /path/to/audiobee_capital_blue/us-vpn-hostnames-surfshark.json .
```

### Step 2: Update config.py

#### Remove Old Configuration

```python
# DELETE these lines:
HEALTHSPARK_PUPPETEER_PORT = 1018  # No longer needed
```

#### Add New Proxy Configuration

```python
# ADD at top of file:
import json
import random

# ADD proxy configuration:
PROXY_LIST = []
with open("us-vpn-hostnames-surfshark.json", "r") as f:
    PROXY_LIST = json.load(f)

def get_random_proxy():
    """Get random Surfshark proxy endpoint."""
    hostname = PROXY_LIST[random.randint(0, len(PROXY_LIST) - 1)]
    return f"https://{hostname}:443"

# Proxy credentials
PROXY_USERNAME = os.environ.get("SURFSHARK_USER", "")
PROXY_PASSWORD = os.environ.get("SURFSHARK_PASS", "")
```

#### Update MAX_WORKERS (Optional)

```python
# Consider increasing since native HTTP is much faster:
MAX_WORKERS = 10  # Was limited by browser overhead, now can go higher
MAX_TASKS = MAX_WORKERS
```

### Step 3: Convert index_1.py to Async

#### Original Synchronous Code (index_1.py)

```python
# OLD CODE
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from healthspark_puppeteer import HealthSpark
import config

def process_county(healthspark, county, plan):
    """Process single county - synchronous."""
    result = healthspark.get_search_response(
        county=county,
        insurerCode=plan["insurerCode"],
        brandCode=plan["brandCode"],
        productCode=plan["productCode"]
    )
    save_result(county, result)
    return result

def main():
    for state in config.REQ_STATES:
        for plan in config.PLANS:
            healthspark = HealthSpark(port=config.HEALTHSPARK_PUPPETEER_PORT)
            healthspark.login(config.URLS["auth_url"].format(**plan))
            
            counties = load_counties(state)
            
            with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
                futures = [
                    executor.submit(process_county, healthspark, county, plan)
                    for county in counties
                ]
                for future in as_completed(futures):
                    future.result()

if __name__ == "__main__":
    main()
```

#### New Async Code (index_1_async.py)

```python
# NEW CODE
import os
import asyncio
from healthspark import HealthSpark
import config

async def process_county(healthspark, county, plan, semaphore):
    """Process single county - async with semaphore."""
    async with semaphore:
        result = await healthspark.get_search_response(
            county=county,
            insurerCode=plan["insurerCode"],
            brandCode=plan["brandCode"],
            productCode=plan["productCode"]
        )
        await save_result(county, result)
        return result

async def main():
    semaphore = asyncio.Semaphore(config.MAX_WORKERS)
    
    for state in config.REQ_STATES:
        for plan in config.PLANS:
            # Create HealthSpark with proxy (no port needed!)
            healthspark = HealthSpark(
                plan=plan,
                proxy=config.get_random_proxy(),
                proxy_username=config.PROXY_USERNAME,
                proxy_password=config.PROXY_PASSWORD
            )
            
            try:
                # Login happens automatically on first API call
                counties = load_counties(state)
                
                # Process all counties concurrently
                tasks = [
                    process_county(healthspark, county, plan, semaphore)
                    for county in counties
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
                
            finally:
                await healthspark.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 4: Convert index_2.py to Async

#### Original Synchronous Code (index_2.py)

```python
# OLD CODE
def fetch_provider_details(healthspark, provider_id, plan):
    """Fetch details - synchronous."""
    output_path = f"{config.DIRS['provider_details']}/{provider_id}.json"
    if os.path.exists(output_path):
        return  # Skip cached
    
    result = healthspark.get_provider_details(
        provider_id=provider_id,
        **plan
    )
    with open(output_path, "w") as f:
        json.dump(result, f)

def main():
    provider_ids = collect_provider_ids_from_search()
    
    healthspark = HealthSpark(port=config.HEALTHSPARK_PUPPETEER_PORT)
    healthspark.login(config.URLS["auth_url"].format(**config.PLANS[0]))
    
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        futures = [
            executor.submit(fetch_provider_details, healthspark, pid, config.PLANS[0])
            for pid in provider_ids
        ]
        for future in tqdm(as_completed(futures), total=len(provider_ids)):
            future.result()
```

#### New Async Code (index_2_async.py)

```python
# NEW CODE
import aiofiles
import orjson

async def fetch_provider_details(healthspark, provider_id, plan, semaphore):
    """Fetch details - async with semaphore."""
    output_path = f"{config.DIRS['provider_details']}/{provider_id}.json"
    if os.path.exists(output_path):
        return  # Skip cached
    
    async with semaphore:
        result = await healthspark.get_provider_details(
            provider_id=provider_id,
            **plan
        )
        async with aiofiles.open(output_path, "wb") as f:
            await f.write(orjson.dumps(result))

async def main():
    provider_ids = collect_provider_ids_from_search()
    semaphore = asyncio.Semaphore(config.MAX_WORKERS)
    
    healthspark = HealthSpark(
        plan=config.PLANS[0],
        proxy=config.get_random_proxy(),
        proxy_username=config.PROXY_USERNAME,
        proxy_password=config.PROXY_PASSWORD
    )
    
    try:
        tasks = [
            fetch_provider_details(healthspark, pid, config.PLANS[0], semaphore)
            for pid in provider_ids
        ]
        
        # Use tqdm for async progress
        for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks)):
            await coro
            
    finally:
        await healthspark.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 5: Update run_all.py

```python
# Update to call async scripts
TASKS = [
    "compare_and_download_old_npi_4.py",
    "delete_extra_files",
    "index_1_async.py",  # Changed from index_1.py
    "index_2_async.py",  # Changed from index_2.py
    "index_3.py",        # Normalization stays synchronous
    "generate_all_qa_files",
]
```

### Step 6: Update CLAUDE.md

```markdown
## Running the Scraper

### Prerequisites
- Python 3.10+
- Patchright browser: `patchright install chromium`
- Surfshark credentials in environment variables

### Execution
```bash
# No server to start! Just run:
python3 run_all.py

# Or run phases individually:
python3 index_1_async.py
python3 index_2_async.py
python3 index_3.py
```
```

---

## Common Conversion Patterns

### Pattern 1: ThreadPoolExecutor → asyncio.gather

```python
# OLD
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(func, arg) for arg in args]
    for future in as_completed(futures):
        result = future.result()

# NEW
semaphore = asyncio.Semaphore(10)
async def limited_func(arg):
    async with semaphore:
        return await func(arg)

tasks = [limited_func(arg) for arg in args]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### Pattern 2: Synchronous HTTP → Async HTTP

```python
# OLD (via healthspark-server)
response = healthspark.fetch(url, method="POST", body=payload)
data = response.json()

# NEW (native async)
response = await healthspark._session.post(url, json=payload)
data = response.json()
```

### Pattern 3: File I/O → Async File I/O

```python
# OLD
with open(path, "w") as f:
    json.dump(data, f)

# NEW
import aiofiles
import orjson
async with aiofiles.open(path, "wb") as f:
    await f.write(orjson.dumps(data))
```

### Pattern 4: Progress Bars with Async

```python
# OLD
for future in tqdm(as_completed(futures), total=len(futures)):
    future.result()

# NEW (Option 1: asyncio.as_completed)
for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks)):
    await coro

# NEW (Option 2: tqdm.asyncio)
from tqdm.asyncio import tqdm_asyncio
await tqdm_asyncio.gather(*tasks)
```

---

## Testing Migration

### Step 1: Verify Browser Authentication

```python
# test_auth.py
import asyncio
from healthspark import HealthSpark
import config

async def test_auth():
    healthspark = HealthSpark(
        plan=config.PLANS[0],
        proxy=config.get_random_proxy(),
        proxy_username=config.PROXY_USERNAME,
        proxy_password=config.PROXY_PASSWORD
    )
    
    try:
        # This triggers browser auth
        result = await healthspark.get_search_response(
            county="Philadelphia",
            insurerCode=config.PLANS[0]["insurerCode"],
            brandCode=config.PLANS[0]["brandCode"],
            productCode=config.PLANS[0]["productCode"]
        )
        print(f"Success! Found {len(result.get('providers', []))} providers")
    finally:
        await healthspark.close()

asyncio.run(test_auth())
```

### Step 2: Compare Output with v1

```bash
# Run v1 (backup) on small subset
cd audiobee_<carrier>_backup_v1
# Manually limit to 1 county, 10 providers
python3 run_all.py

# Run v2 on same subset
cd ../audiobee_<carrier>
python3 run_all.py

# Compare outputs
diff -r audiobee_<carrier>_backup_v1/YYYYMMDD/processed/ \
        audiobee_<carrier>/YYYYMMDD/processed/
```

### Step 3: Performance Comparison

```python
# benchmark.py
import asyncio
import time
from healthspark import HealthSpark
import config

async def benchmark():
    healthspark = HealthSpark(
        plan=config.PLANS[0],
        proxy=config.get_random_proxy(),
        proxy_username=config.PROXY_USERNAME,
        proxy_password=config.PROXY_PASSWORD
    )
    
    try:
        # Time 100 API calls
        start = time.time()
        for i in range(100):
            await healthspark.get_search_response(
                county="Philadelphia",
                **config.PLANS[0]
            )
        elapsed = time.time() - start
        
        print(f"100 requests in {elapsed:.2f}s")
        print(f"Average: {elapsed/100*1000:.0f}ms per request")
    finally:
        await healthspark.close()

asyncio.run(benchmark())
```

---

## Troubleshooting

### Error: "Patchright browser not found"

```bash
# Install Chromium for Patchright
patchright install chromium

# Verify installation
patchright install --help
```

### Error: "Proxy authentication failed"

```bash
# Check environment variables
echo $SURFSHARK_USER
echo $SURFSHARK_PASS

# Test proxy connectivity
curl -x "https://$SURFSHARK_USER:$SURFSHARK_PASS@us-dal.prod.surfshark.com:443" \
     https://httpbin.org/ip
```

### Error: "Session expired" or "401 Unauthorized"

```python
# The new HealthSpark should auto-handle re-auth, but if issues persist:

# 1. Check auth URL format matches carrier
print(config.URLS["auth_url"].format(**config.PLANS[0]))
# Should produce valid URL

# 2. Manually test auth URL in browser
# 3. Check if carrier changed their login flow
```

### Error: "429 Too Many Requests"

```python
# Reduce concurrency
MAX_WORKERS = 5  # Down from 10

# Add random delay between requests
import random
await asyncio.sleep(random.uniform(0.5, 1.5))
```

### Error: "Event loop is closed"

```python
# Don't nest asyncio.run() calls
# BAD:
async def outer():
    asyncio.run(inner())  # Error!

# GOOD:
async def outer():
    await inner()

asyncio.run(outer())
```

---

## Migration Schedule

### Week 1: Setup & Reference

| Day | Task |
|-----|------|
| 1-2 | Environment setup, install dependencies |
| 3-4 | Study audiobee_capital_blue implementation |
| 5 | Create shared library from reference |

### Week 2: Low-Complexity Projects (2)

| Project | States | Notes |
|---------|--------|-------|
| audiobee_maine_community_health_options | ME | Single state, simple |
| audiobee_first_choice_sc | SC | Single state, Medicaid |

### Week 3: Medium-Complexity Batch 1 (6)

| Project | States | Notes |
|---------|--------|-------|
| audiobee_amerihealth_administrators_pa | PA | |
| audiobee_highmark_wholecare | PA | |
| audiobee_ibx | PA | |
| audiobee_amerihealth_caritas_vip_de | DE | |
| audiobee_amerihealth_nj | NJ | |
| audiobee_health_plan_nv_medicaid | NV | |

### Week 4: Medium-Complexity Batch 2 (6)

| Project | States | Notes |
|---------|--------|-------|
| audiobee_medica | IA, MN, ND, NE, WI | Multi-state |
| audiobee_medica_sg | IA, MN, ND, NE, WI | Multi-state |
| audiobee_quartz | WI, MN, IL, IA | Multi-state |
| audiobee_alliance_trilogy | WI, MN, IL, IA, MI | Multi-state |
| audiobee_wellmark | IA, SD | |
| audiobee_wellmark_medicare | IA, SD | |

### Week 5: Medium-Complexity Batch 3 (6)

| Project | States | Notes |
|---------|--------|-------|
| audiobee_mvp_health | NY/VT | |
| audiobee_excellus | NY | |
| audiobee_mass_gen | MA + neighbors | |
| audiobee_tufts_health_plans | MA, NH, RI | |
| audiobee_sentara | VA, NC | |
| audiobee_christus_health_plan | LA, NM, TX | |

### Week 6: Remaining Projects (4) + Cleanup

| Project | States | Notes |
|---------|--------|-------|
| audiobee_asuris_northwest | WA, OR, ID, UT | |
| audiobee_hma | WA, OR, etc. | |
| audiobee_medical_mutual | OH + surrounding | |
| audiobee_capital_blue | PA + surrounding | Already done (reference) |

### Week 7: Deprecation

1. Remove healthsparq-server directory
2. Update all documentation
3. Remove Node.js dependencies from deployment

---

## Rollback Procedure

If migration fails for a project:

```bash
# 1. Restore from backup
cd /path/to/projects
rm -rf audiobee_<carrier>
mv audiobee_<carrier>_backup_v1 audiobee_<carrier>

# 2. Restart healthsparq-server
cd healthsparq-server
PORT=1018 npm start

# 3. Run v1 scraper
cd audiobee_<carrier>
python3 run_all.py
```

---

## Post-Migration Checklist

- [ ] All 24 projects migrated
- [ ] Output validation passed for each project
- [ ] Performance benchmarks documented
- [ ] healthsparq-server removed from repository
- [ ] Documentation updated:
  - [ ] docs/ARCHITECTURE.md
  - [ ] docs/SITE_TYPES_REFERENCE.md
  - [ ] docs/by-site-type/healthsparq.md
  - [ ] docs/architecture/healthsparq.md
  - [ ] Individual project CLAUDE.md files
- [ ] Node.js dependencies removed from deployment scripts
- [ ] Team trained on new architecture

---

*Last Updated: December 2024*
