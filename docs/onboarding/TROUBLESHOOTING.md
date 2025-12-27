# Troubleshooting Guide

> **Comprehensive Problem Resolution for Ideon Scraping Infrastructure**

## Quick Diagnostic Flowchart

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ISSUE DIAGNOSIS FLOW                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Scraper not working?                                                   │
│         │                                                                │
│         ▼                                                                │
│  ┌──────────────────┐   YES   ┌─────────────────────────────────────┐  │
│  │ Connection error?│────────▶│ Check: healthsparq-server running?  │  │
│  └────────┬─────────┘         │        Network connectivity?        │  │
│           │NO                 │        Proxy configuration?         │  │
│           ▼                   └─────────────────────────────────────┘  │
│  ┌──────────────────┐   YES   ┌─────────────────────────────────────┐  │
│  │  403/401 error?  │────────▶│ Check: API key valid?               │  │
│  └────────┬─────────┘         │        Headers correct?             │  │
│           │NO                 │        IP blocked?                  │  │
│           ▼                   └─────────────────────────────────────┘  │
│  ┌──────────────────┐   YES   ┌─────────────────────────────────────┐  │
│  │  429 rate limit? │────────▶│ Check: Add delays between requests  │  │
│  └────────┬─────────┘         │        Reduce concurrency          │  │
│           │NO                 │        Wait and retry               │  │
│           ▼                   └─────────────────────────────────────┘  │
│  ┌──────────────────┐   YES   ┌─────────────────────────────────────┐  │
│  │  Empty output?   │────────▶│ Check: Search params correct?       │  │
│  └────────┬─────────┘         │        Geographic coverage?        │  │
│           │NO                 │        Network ID valid?            │  │
│           ▼                   └─────────────────────────────────────┘  │
│  ┌──────────────────┐   YES   ┌─────────────────────────────────────┐  │
│  │ Validation fail? │────────▶│ Check: Missing required fields?     │  │
│  └────────┬─────────┘         │        Data type mismatches?       │  │
│           │NO                 │        Schema changes?              │  │
│           ▼                   └─────────────────────────────────────┘  │
│  ┌──────────────────┐                                                  │
│  │  Other issue     │───────▶ Check logs and error messages           │
│  └──────────────────┘                                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Connection Issues

### Problem: "Connection refused" to healthsparq-server

**Symptoms:**
```
ConnectionRefusedError: [Errno 111] Connection refused
requests.exceptions.ConnectionError: HTTPConnectionPool(host='localhost', port=1018)
```

**Solutions:**

```bash
# 1. Check if server is running
ps aux | grep node

# 2. Start the server
cd /Users/dikson/Work/ideon_scraping/scraping/healthsparq-server
npm start

# 3. Check configured port matches project config
grep HEALTHSPARK_PUPPETEER_PORT /path/to/project/config.py
# Example output: HEALTHSPARK_PUPPETEER_PORT = 1012

# 4. Start on specific port
PORT=1012 npm start

# 5. Test server is responding
curl http://localhost:1012/health
```

**Root Causes:**
- Server not started
- Wrong port configured
- Port already in use
- Server crashed

---

### Problem: Timeout errors

**Symptoms:**
```
httpx.TimeoutException: Read timed out
asyncio.TimeoutError
socket.timeout: timed out
```

**Solutions:**

```python
# 1. Increase timeout in requests
import httpx
response = httpx.get(url, timeout=60.0)  # Increase from default 30s

# 2. For async operations
response = await browser.fetch(url, timeout=120000)  # 120 seconds

# 3. Add retry logic
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=4, max=60))
def fetch_with_retry(url):
    return httpx.get(url, timeout=60)
```

**Root Causes:**
- Slow API response
- Network congestion
- Server overloaded
- Large response payload

---

### Problem: SSL Certificate errors

**Symptoms:**
```
ssl.SSLCertVerificationError: certificate verify failed
requests.exceptions.SSLError
```

**Solutions:**

```python
# 1. Update certifi package
pip install --upgrade certifi

# 2. If using self-signed cert (not recommended for production)
import httpx
response = httpx.get(url, verify=False)

# 3. Specify certificate path
import ssl
ssl_context = ssl.create_default_context(cafile="/path/to/cert.pem")
```

---

## Authentication Errors

### Problem: 401 Unauthorized

**Symptoms:**
```
HTTP 401 Unauthorized
{"error": "Invalid credentials"}
{"message": "Authentication required"}
```

**Solutions:**

```python
# 1. Check API key in config.py
# Verify it matches the carrier's documentation

# 2. Check header format
HEADERS = {
    "Authorization": "Bearer your-token",  # or
    "X-API-Key": "your-api-key",           # or
    "Api-Key": "your-api-key",
}

# 3. Check if token expired (JWT tokens)
import jwt
token = "your-jwt-token"
decoded = jwt.decode(token, options={"verify_signature": False})
print(f"Expires: {decoded.get('exp')}")

# 4. Regenerate token if needed
# Follow carrier-specific authentication flow
```

---

### Problem: 403 Forbidden

**Symptoms:**
```
HTTP 403 Forbidden
{"error": "Access denied"}
{"message": "IP not whitelisted"}
```

**Solutions:**

```bash
# 1. Check if IP is blocked
curl -I https://api.carrier.com/health

# 2. Use proxy rotation
# In config.py:
PROXY_URL = "socks5://user:pass@proxy.example.com:1080"

# 3. Reduce request rate
# Add delays between requests
import time
time.sleep(1)  # 1 second between requests

# 4. Check User-Agent
# Some APIs block bot-like User-Agents
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
```

**Root Causes:**
- IP address blocked
- Rate limit exceeded
- Bot detection triggered
- Invalid API permissions

---

### Problem: Session expired (Healthsparq)

**Symptoms:**
```
{"error": "Session expired"}
{"message": "Please login again"}
HTTP 401 after initial success
```

**Solutions:**

```python
# 1. Restart healthsparq-server
# This creates a fresh browser session

# 2. Re-authenticate in the scraper
def refresh_session():
    response = requests.post(
        f"{SERVER_URL}/setBaseUrl",
        json={"baseUrl": config.BASE_URL}
    )
    return response.json()

# 3. Add session refresh logic
if response.status_code == 401:
    refresh_session()
    # Retry the request
```

---

## Rate Limiting

### Problem: 429 Too Many Requests

**Symptoms:**
```
HTTP 429 Too Many Requests
{"error": "Rate limit exceeded"}
{"retry_after": 60}
```

**Solutions:**

```python
# 1. Honor Retry-After header
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", 60))
    print(f"Rate limited, waiting {retry_after}s")
    time.sleep(retry_after)

# 2. Reduce concurrency
MAX_WORKERS = 5  # Reduce from 10

# 3. Add delays between requests
import random
time.sleep(random.uniform(0.5, 1.5))  # Random delay

# 4. Implement exponential backoff
from tenacity import retry, wait_exponential

@retry(wait=wait_exponential(multiplier=1, min=4, max=60))
def fetch_with_backoff(url):
    response = httpx.get(url)
    if response.status_code == 429:
        raise Exception("Rate limited")
    return response
```

---

### Problem: 418 I'm a Teapot (Anti-bot)

**Symptoms:**
```
HTTP 418 I'm a teapot
Bot detection triggered
```

**Solutions:**

```python
# 1. Use stealth browser (Camoufox)
from camoufox import Camoufox

async with Camoufox(headless=True) as browser:
    page = await browser.new_page()
    await page.goto(url)

# 2. Add random delays
import random
time.sleep(random.uniform(2, 5))

# 3. Rotate User-Agent
from browserforge.headers import HeaderGenerator
headers = HeaderGenerator().generate()

# 4. Use proxy rotation
proxies = [
    "socks5://proxy1:port",
    "socks5://proxy2:port",
]
proxy = random.choice(proxies)

# 5. For Provider Lenz: Use CAPTCHA solver
from capsolver_local import capsolver_fn
solution = await capsolver_fn(captcha_data)
```

---

## Data Issues

### Problem: Empty output file

**Symptoms:**
```
0 records written to output
Empty JSONL file
```

**Diagnostic Steps:**

```bash
# 1. Check Phase 1 output
ls -la 20251110/raw/search_results/
# Should contain JSON files

# 2. Check search results content
head -5 20251110/raw/search_results/*.json | head -50

# 3. Check Phase 2 output
ls -la 20251110/raw/provider_details/
# Should contain provider JSON files

# 4. Check for errors in logs
python index_1.py 2>&1 | grep -i error
```

**Common Causes & Solutions:**

```python
# 1. Wrong network_id
# Verify network ID is valid for the carrier
print(f"Using network_id: {config.BASE_PARAMS['network_id']}")

# 2. Wrong geographic coordinates
# Check GEO_COORDS covers the target states
GEO_COORDS = "39.883875,-88.834467"  # IL center
RADIUS = "210"  # miles - must cover entire state

# 3. No results for specialty
# Try different specialties or remove specialty filter

# 4. Date directory not created
os.makedirs(config.DIRS["search_results"], exist_ok=True)
```

---

### Problem: Missing required fields

**Symptoms:**
```
ValidationError: 'npi' is a required property
ValidationError: 'unparsed_name' is a required property
```

**Solutions:**

```python
# In index_3.py, ensure required fields are always populated

def map_provider(raw: dict) -> dict:
    # NPI extraction with fallback
    npi = None
    for identifier in raw.get("identifiers", []):
        if identifier.get("type_code") == "NPI":
            npi = identifier.get("value")
            break

    # Name with fallback
    unparsed_name = raw.get("name") or raw.get("full_name") or "Unknown"

    return {
        "provider": {
            "npi": npi,  # Can be None
            "unparsed_name": unparsed_name,  # Required
            "provider_type": raw.get("provider_type", "individual"),
            # ...
        }
    }
```

---

### Problem: Duplicate NPIs in output

**Symptoms:**
```
Multiple records with same NPI
Inconsistent data for same provider
```

**Solutions:**

```python
# Verify deduplication in index_3.py

def deduplicate_by_npi(items: list) -> list:
    npi_map = {}
    no_npi = []

    for item in items:
        npi = item["provider"]["npi"]

        if npi is None:
            no_npi.append(item)
            continue

        if npi not in npi_map:
            npi_map[npi] = item
        else:
            # Merge records
            existing = npi_map[npi]

            # Merge networks
            existing_networks = {n["name"]: n for n in existing["networks"]}
            for network in item["networks"]:
                existing_networks[network["name"]] = network
            existing["networks"] = list(existing_networks.values())

            # Merge addresses (by external_id)
            existing_addrs = {a.get("external_id"): a for a in existing["addresses"]}
            for addr in item["addresses"]:
                ext_id = addr.get("external_id")
                if ext_id and ext_id not in existing_addrs:
                    existing_addrs[ext_id] = addr
            existing["addresses"] = list(existing_addrs.values())

    return list(npi_map.values()) + no_npi
```

---

### Problem: Wrong state in output

**Symptoms:**
```
Providers from states not in REQ_STATES
State field has wrong value
```

**Solutions:**

```python
# 1. Filter in Phase 3
def filter_by_state(item: dict, req_states: list) -> bool:
    for address in item.get("addresses", []):
        if address.get("state") in req_states:
            return True
    return False

# Apply filter
filtered_items = [
    item for item in items
    if filter_by_state(item, config.REQ_STATES)
]

# 2. Filter in Phase 1 (better performance)
# Only search for providers in target states
for state in config.REQ_STATES:
    search_state(state)
```

---

## Schema Validation Errors

### Problem: type_check.py failures

**Symptoms:**
```
Schema validation failed
Invalid type for field X
Missing required field Y
```

**Diagnostic:**

```bash
# Run with verbose output
python output_generator/type_check.py audiobee_project/ 2>&1 | head -100

# Check specific record
python -c "
import orjson
with open('20251110/processed/project.jsonl', 'r') as f:
    for i, line in enumerate(f):
        try:
            data = orjson.loads(line)
        except:
            print(f'Invalid JSON at line {i}')
        if i >= 10:
            break
"
```

**Common Schema Issues:**

```python
# Issue: ZIP code wrong format
# Fix: Ensure 5-digit string
zip_code = str(raw.get("postal_code", ""))[:5]
if len(zip_code) < 5:
    zip_code = zip_code.zfill(5)  # Pad with zeros

# Issue: Phone format
# Fix: Clean to digits only
import re
phone = re.sub(r'[^0-9]', '', raw.get("phone", ""))

# Issue: State code format
# Fix: Uppercase 2-letter code
state = raw.get("state", "").upper()[:2]

# Issue: Provider type
# Fix: Must be "individual" or "organization"
provider_type = "individual" if raw.get("type") == "P" else "organization"

# Issue: Boolean fields
# Fix: Must be True/False, not "Y"/"N"
accepting = raw.get("accepting") in ["Y", "Yes", "true", True]
```

---

## Performance Issues

### Problem: Scraper running too slowly

**Symptoms:**
```
Phase 1 taking hours
Only processing 10 requests/minute
```

**Solutions:**

```python
# 1. Increase concurrency
MAX_WORKERS = 10  # Up from 5

# 2. Use async for I/O bound operations
import asyncio
import aiohttp

async def fetch_all(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_one(session, url) for url in urls]
        return await asyncio.gather(*tasks)

# 3. Use connection pooling
import httpx
with httpx.Client(limits=httpx.Limits(max_connections=20)) as client:
    # All requests share connection pool

# 4. Batch file writes
# Write in batches instead of per-record
batch = []
for item in items:
    batch.append(item)
    if len(batch) >= 1000:
        write_batch(batch)
        batch = []

# 5. Use orjson for faster JSON
import orjson  # 10x faster than json
data = orjson.loads(response.content)
```

---

### Problem: Out of memory

**Symptoms:**
```
MemoryError
Process killed
System becomes unresponsive
```

**Solutions:**

```python
# 1. Process in chunks
def process_large_file(filepath):
    with open(filepath, 'r') as f:
        for line in f:  # Streaming, not loading entire file
            process(orjson.loads(line))

# 2. Use generators
def load_providers():
    for file in Path(config.DIRS["provider_details"]).glob("*.json"):
        with open(file, 'rb') as f:
            yield orjson.loads(f.read())

# For item in load_providers():  # Memory efficient
#     process(item)

# 3. Clear large objects
del large_list
import gc
gc.collect()

# 4. Reduce batch size
BATCH_SIZE = 500  # Down from 1000
```

---

## Pipeline Recovery

### Problem: Pipeline failed mid-execution

**Symptoms:**
```
Pipeline stopped at Phase 2
Partial data in output directories
```

**Recovery Steps:**

```bash
# 1. Check what was completed
ls -la 20251110/raw/search_results/  # Phase 1 output
ls -la 20251110/raw/provider_details/  # Phase 2 output

# 2. If Phase 1 complete, skip to Phase 2
python index_2.py

# 3. If Phase 2 partial, it will resume (files are cached)
# Just re-run:
python index_2.py

# 4. Re-run normalization
python index_3.py

# 5. Or use run_all.py with error handling
# It will fail fast but you can restart from last checkpoint
```

**Adding Checkpoint Recovery:**

```python
# In index_2.py
def should_skip(provider_id):
    output_path = f"{config.DIRS['provider_details']}/{provider_id}.json"
    return os.path.exists(output_path)

for provider_id in provider_ids:
    if should_skip(provider_id):
        continue  # Already fetched
    fetch_and_save(provider_id)
```

---

## Log Analysis

### Useful Log Patterns

```bash
# Find all errors
grep -i "error" run.log

# Find rate limiting
grep -i "429\|rate\|limit" run.log

# Find timeouts
grep -i "timeout\|timed out" run.log

# Find HTTP status codes
grep -oE "HTTP [0-9]{3}" run.log | sort | uniq -c

# Find slow requests (if timing logged)
grep -E "took [0-9]+s" run.log | sort -t' ' -k2 -n -r | head -10
```

### Adding Better Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler('run.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Usage
logger.info(f"Starting Phase 1")
logger.warning(f"Rate limited, waiting {seconds}s")
logger.error(f"Failed to fetch {provider_id}: {e}")
logger.debug(f"Response: {response.text[:200]}")
```

---

## Quick Reference: Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| 200 | Success | N/A |
| 400 | Bad Request | Check request parameters |
| 401 | Unauthorized | Check API key/token |
| 403 | Forbidden | Check IP, permissions |
| 404 | Not Found | Check URL, provider ID |
| 418 | Bot Detection | Use stealth, delays |
| 429 | Rate Limited | Add delays, reduce concurrency |
| 500 | Server Error | Retry later |
| 502 | Bad Gateway | Retry later |
| 503 | Service Unavailable | Retry later |

---

## Getting Additional Help

1. **Check existing documentation:**
   - [ARCHITECTURE.md](./ARCHITECTURE.md)
   - [PIPELINE.md](./PIPELINE.md)
   - [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)

2. **Review similar projects:**
   - Find a working project of same site type
   - Compare config.py and index files

3. **Enable verbose logging:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

4. **Test API manually:**
   ```bash
   curl -v "https://api.example.com/endpoint" \
     -H "X-API-Key: your-key"
   ```

---

*Last Updated: December 2024*
