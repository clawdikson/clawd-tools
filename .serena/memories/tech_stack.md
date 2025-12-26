# Technology Stack

## Python (Primary Language)
- **Version**: Python 3.11+
- **Package Management**: `uv` (pyproject.toml per project)

## Core Libraries

### HTTP/Requests
- `httpx` / `requests` - HTTP client for API calls
- `curl_cffi` - HTTP with browser impersonation (anti-detection)
- `tenacity` - Retry logic with decorators

### Browser Automation
- `camoufox` - Anti-detection browser (Firefox-based)
- `patchright` - Playwright fork with anti-detection
- `playwright` - Standard browser automation

### Data Processing
- `orjson` - Fast JSON serialization (preferred over standard json)
- `pandas` - Data manipulation
- `numpy` - Numerical operations

### Async
- `asyncio` - Async/await patterns
- `aiofiles` - Async file I/O

### Utilities
- `tqdm` - Progress bars
- `browserforge` - Header generation for anti-detection
- `python-dotenv` - Environment variable management

## Node.js (healthsparq-server)
- Puppeteer for browser automation
- Express.js for server
- Port 1018

## Proxies
- DataImpulse (primary)
- NordVPN (via shared_package)
- Surfshark (via shared_package)

## File Formats
- **Raw data**: JSON, JSONL
- **Processed output**: JSONL (normalized schema)
- **Reports**: Excel (.xlsx)
- **Archives**: 7z compression

## Key Patterns
- `orjson.loads(f.read())` for reading JSON (not json.load)
- `orjson.dumps(data).decode()` for writing
- `asyncio.gather()` for concurrent operations
- `@retry(stop=stop_after_attempt(3))` for retry logic
