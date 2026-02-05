# Healthsparq Scraper Architecture v2

> **Updated architecture using embedded Python browser automation (replacing healthsparq-server)**

---

## Overview

Healthsparq scrapers extract provider directory data from insurance carriers using the Healthsparq platform. The v2 architecture eliminates the external Node.js healthsparq-server in favor of embedded Python browser automation.

### Architecture Evolution

| Version | Browser Management | HTTP Client | Concurrency |
|---------|-------------------|-------------|-------------|
| v1 (deprecated) | External Node.js server | Browser fetch() | ThreadPoolExecutor |
| **v2 (current)** | Embedded Patchright | curl_cffi | asyncio |

---

## System Topology

```
┌─────────────────────────────────────────────────────────────────────┐
│                    HEALTHSPARQ v2 ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    Python Scraper Process                      │ │
│  │                                                                │ │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │ │
│  │  │  config.py  │    │ healthspark │    │index_1_async│       │ │
│  │  │             │───►│    .py      │◄───│    .py      │       │ │
│  │  │ Proxy list  │    │             │    │             │       │ │
│  │  │ Plan codes  │    │ Session mgmt│    │ County grid │       │ │
│  │  └─────────────┘    └──────┬──────┘    └─────────────┘       │ │
│  │                            │                                   │ │
│  │                 ┌──────────┴──────────┐                       │ │
│  │                 │                     │                       │ │
│  │          ┌──────▼──────┐       ┌──────▼──────┐               │ │
│  │          │BrowserSession│       │ HttpSession │               │ │
│  │          │             │       │             │               │ │
│  │          │  Patchright │       │  curl_cffi  │               │ │
│  │          │  (login)    │       │  (API calls)│               │ │
│  │          └──────┬──────┘       └──────┬──────┘               │ │
│  │                 │                     │                       │ │
│  │          Login once            Native HTTP                    │ │
│  │          Extract cookies       Chrome TLS fingerprint         │ │
│  │          Close browser         10-100x faster                 │ │
│  │                                                                │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                      External Services                         │ │
│  │                                                                │ │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │ │
│  │  │  Surfshark  │    │ Healthsparq │    │  File       │       │ │
│  │  │  Proxies    │    │    APIs     │    │  System     │       │ │
│  │  │  (port 443) │    │             │    │             │       │ │
│  │  └─────────────┘    └─────────────┘    └─────────────┘       │ │
│  │                                                                │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. BrowserSession (browser_session.py)

Manages Patchright browser instances for authentication:

```python
from patchright.async_api import async_playwright

class BrowserSession:
    """
    Patchright-based browser for login/auth extraction.
    
    Key features:
    - Chromium with proxy server args
    - HTTP Basic Auth via browser context
    - Cookie/user-agent extraction for HttpSession
    - Auto-closes after auth (memory efficiency)
    """
    
    async def login(self, auth_url: str) -> None:
        """Navigate to auth URL and establish session."""
        
    async def get_cookies(self) -> list[dict]:
        """Extract cookies for HttpSession initialization."""
        
    async def get_user_agent(self) -> str:
        """Get browser user agent for HttpSession."""
        
    async def close(self) -> None:
        """Close browser (called after auth extraction)."""
```

### 2. HttpSession (browser_session.py)

Native HTTP client using curl_cffi for API calls:

```python
from curl_cffi.requests import AsyncSession

class HttpSession:
    """
    curl_cffi-based HTTP client with Chrome TLS fingerprint.
    
    Key features:
    - 10-100x faster than browser automation
    - Chrome TLS fingerprint impersonation
    - Initialized from browser cookies/user-agent
    - Proxy authentication support
    """
    
    async def initialize_from_browser(
        self, 
        cookies: list[dict], 
        user_agent: str,
        proxy: str
    ) -> None:
        """Initialize with cookies from BrowserSession."""
        
    async def get(self, url: str, **kwargs) -> Response:
        """Native HTTP GET with Chrome fingerprint."""
        
    async def post(self, url: str, **kwargs) -> Response:
        """Native HTTP POST with Chrome fingerprint."""
```

### 3. HealthSpark (healthspark.py)

Session manager combining browser auth with native HTTP:

```python
class HealthSpark:
    """
    Hybrid session manager for Healthsparq API.
    
    Flow:
    1. Create BrowserSession with proxy
    2. Login via browser (extracts cookies)
    3. Create HttpSession from browser cookies
    4. Close browser (no longer needed)
    5. All API calls use native HttpSession
    """
    
    async def _ensure_session(self) -> None:
        """Lazy initialization with browser→HTTP handoff."""
        async with self._session_lock:
            if self._session is None:
                # Browser for auth only
                await self._browser_session.login(auth_url)
                cookies = await self._browser_session.get_cookies()
                user_agent = await self._browser_session.get_user_agent()
                
                # Native HTTP for all subsequent calls
                self._session = HttpSession()
                await self._session.initialize_from_browser(
                    cookies, user_agent, self._proxy
                )
                
                # Release browser memory
                await self._browser_session.close()
                self._browser_session = None
    
    async def get_search_response(self, **params) -> dict:
        """Search providers via native HTTP."""
        
    async def get_provider_details(self, provider_id: str) -> dict:
        """Get provider details via native HTTP."""
```

---

## Execution Flow

### Phase 1: Search/Discovery (index_1_async.py)

```python
async def main():
    for state in config.REQ_STATES:
        for plan in config.PLANS:
            # Create HealthSpark instance per state/plan
            healthspark = HealthSpark(
                plan=plan,
                proxy=config.get_random_proxy()
            )
            
            try:
                # Login happens automatically on first API call
                counties = load_counties(state)
                
                # Process counties concurrently with semaphore
                async with asyncio.TaskGroup() as tg:
                    for county in counties:
                        tg.create_task(
                            process_county(healthspark, county)
                        )
            finally:
                await healthspark.close()
```

### Phase 2: Detail Extraction (index_2_async.py)

```python
async def main():
    # Load provider IDs from Phase 1
    provider_ids = collect_provider_ids()
    
    healthspark = HealthSpark(
        plan=config.PLANS[0],
        proxy=config.get_random_proxy()
    )
    
    try:
        # Fetch details with semaphore control
        semaphore = asyncio.Semaphore(config.MAX_WORKERS)
        
        async def fetch_with_limit(provider_id):
            async with semaphore:
                return await healthspark.get_provider_details(provider_id)
        
        tasks = [fetch_with_limit(pid) for pid in provider_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        await healthspark.close()
```

---

## Configuration

### config.py Template

```python
import os
import json
import random

# Dates
PREV_DATE = "20251101"
CURR_DATE = "20251201"
PROJECT_NAME = "audiobee_<carrier>"

# Concurrency (adjust based on carrier tolerance)
MAX_WORKERS = 10  # Concurrent API requests
MAX_TASKS = MAX_WORKERS

# Plans to scrape
PLANS = [
    {"insurerCode": "XXX_I", "brandCode": "XXX", "productCode": "all"},
]

# Target states
REQ_STATES = ["PA", "OH", "WV", "MD", "DE", "NJ", "NY", "DC"]
REQ_STATES_ONLY = ["PA"]  # Primary state only

# Directories
DIRS = {
    "raw": os.path.join(CURR_DATE, "raw"),
    "search_results": os.path.join(CURR_DATE, "raw", "search_results"),
    "provider_details": os.path.join(CURR_DATE, "raw", "provider_details"),
    "processed": os.path.join(CURR_DATE, "processed"),
    "geocode_results": "geocode_results",
}
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

# Healthsparq URLs
URLS = {
    "auth_url": "https://<carrier>.healthsparq.com/healthsparq/public/#/one/insurerCode={insurerCode}&brandCode={brandCode}",
    "search_url": "https://<carrier>.healthsparq.com/healthsparq/public/service/v4/search",
    "profile_url": "https://<carrier>.healthsparq.com/healthsparq/public/service/profile",
    "profile_url_v2": "https://<carrier>.healthsparq.com/healthsparq/public/service/v2/profile",
    "filter_url": "https://<carrier>.healthsparq.com/healthsparq/public/service/v3/search/filters",
    "geocode_url": "https://<carrier>.healthsparq.com/healthsparq/public/service/geocode",
}

# Proxy configuration (Surfshark)
PROXY_LIST = []
with open("us-vpn-hostnames-surfshark.json", "r") as f:
    PROXY_LIST = json.load(f)

def get_random_proxy():
    """Get random Surfshark proxy endpoint."""
    hostname = PROXY_LIST[random.randint(0, len(PROXY_LIST) - 1)]
    return f"https://{hostname}:443"

# Proxy credentials (loaded from environment or secrets)
PROXY_USERNAME = os.environ.get("SURFSHARK_USER", "")
PROXY_PASSWORD = os.environ.get("SURFSHARK_PASS", "")
```

---

## Directory Structure

```
audiobee_<carrier>/
├── config.py                    # Configuration
├── healthspark.py               # HealthSpark client (or import from lib)
├── browser_session.py           # Browser/HTTP sessions (or import from lib)
├── index_1_async.py             # Phase 1: Discovery (async)
├── index_2_async.py             # Phase 2: Extraction (async)
├── index_3.py                   # Phase 3: Normalization
├── run_all.py                   # Pipeline orchestrator
├── CLAUDE.md                    # Project documentation
├── us-vpn-hostnames-surfshark.json  # Proxy endpoints
│
├── YYYYMMDD/                    # Date-versioned output
│   ├── raw/
│   │   ├── search_results/      # Phase 1 JSON
│   │   └── provider_details/    # Phase 2 JSON
│   └── processed/
│       └── <project>-YYYYMMDD.jsonl
│
└── geocode_results/             # Cached geocode lookups
```

---

## Operational Runbook

### Prerequisites

```bash
# Python 3.10+ with async support
python3 --version

# Install dependencies
pip install patchright curl_cffi aiofiles orjson tenacity tqdm

# Install Patchright browser
patchright install chromium
```

### Running the Pipeline

```bash
cd audiobee_<carrier>

# No server to start! Just run the pipeline.
python3 run_all.py

# Or run phases individually:
python3 index_1_async.py  # Discovery
python3 index_2_async.py  # Extraction
python3 index_3.py        # Normalization
```

### Monitoring Progress

```bash
# Watch output directory growth
watch -n 5 'find YYYYMMDD/raw -name "*.json" | wc -l'

# Check for errors
tail -f scraper.log | grep -i error
```

---

## Troubleshooting

### Browser Launch Failures

```python
# Error: Browser failed to launch
# Solution: Install Patchright browser
patchright install chromium

# Error: Proxy authentication failed
# Solution: Check SURFSHARK_USER and SURFSHARK_PASS environment variables
export SURFSHARK_USER="your-username"
export SURFSHARK_PASS="your-password"
```

### Session Errors

```python
# Error: Session expired / 401 Unauthorized
# Solution: HealthSpark auto-handles re-auth, but check:
# 1. Proxy is working
# 2. Credentials are valid
# 3. Auth URL format is correct for carrier
```

### Rate Limiting

```python
# Error: 429 Too Many Requests
# Solution: Reduce MAX_WORKERS in config.py
MAX_WORKERS = 5  # Down from 10

# Error: 403 Forbidden (bot detection)
# Solution: 
# 1. Reduce concurrency
# 2. Add random delays
# 3. Rotate to different proxy
```

---

## Migration from v1 (healthsparq-server)

### Before (v1)

```bash
# Terminal 1: Start Node.js server
cd healthsparq-server
PORT=1018 npm start

# Terminal 2: Run scraper
cd audiobee_<carrier>
python3 run_all.py
```

### After (v2)

```bash
# Single terminal, no server required
cd audiobee_<carrier>
python3 run_all.py
```

### Code Changes Required

1. **Remove server dependency**:
   ```python
   # Delete this line from config.py:
   HEALTHSPARK_PUPPETEER_PORT = 1018
   ```

2. **Update imports**:
   ```python
   # OLD:
   from healthspark_puppeteer import HealthSpark
   
   # NEW:
   from healthspark import HealthSpark
   ```

3. **Convert to async**:
   ```python
   # OLD (synchronous):
   def process_county(county):
       healthspark.get_search_response(county=county)
   
   # NEW (async):
   async def process_county(county):
       await healthspark.get_search_response(county=county)
   ```

---

## Performance Comparison

| Metric | v1 (healthsparq-server) | v2 (embedded) | Improvement |
|--------|-------------------------|---------------|-------------|
| Request latency | 500-1000ms | 50-100ms | 10x |
| Memory usage | 200-300MB | 50-100MB | 3x |
| Startup time | 10-15s (server start) | 2-3s (browser auth) | 5x |
| Deployment | 2 processes | 1 process | Simpler |
| Dependencies | Node.js + Python | Python only | Simpler |

---

## Related Documentation

- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture overview
- [PIPELINE.md](../PIPELINE.md) - Pipeline phase details
- [DEVELOPER_GUIDE.md](../DEVELOPER_GUIDE.md) - Development guide
- [healthsparq.md](../by-site-type/healthsparq.md) - Project listing

---

*Last Updated: December 2024*
