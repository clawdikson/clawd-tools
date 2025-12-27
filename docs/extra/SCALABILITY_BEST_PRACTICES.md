# Scalability Best Practices for Python Web Scraping at Scale (100+ Scrapers)

## Executive Summary

This document compiles industry best practices for building and managing large-scale web scraping infrastructure (100+ scrapers). The guidance focuses on **stdlib + minimal dependencies**, drawing from authoritative sources and real-world implementations.

**Key Principles:**
- **I/O-bound operations**: Use `asyncio` + `aiohttp` (10x faster than synchronous)
- **CPU-bound operations**: Use `ProcessPoolExecutor` for parsing/processing
- **Memory efficiency**: Generator patterns + streaming (avoid loading full datasets)
- **Rate limiting**: Semaphores + leaky bucket algorithms (10-30 RPS is respectful)
- **Error recovery**: Circuit breaker pattern + exponential backoff
- **Monitoring**: Counters, gauges, histograms for production visibility

---

## 1. Parallel Execution Patterns

### 1.1 When to Use What

| Scenario | Solution | Reason |
|----------|----------|--------|
| **HTTP requests** (I/O-bound) | `asyncio` + `aiohttp` | Processor idle waiting for network responses |
| **HTML parsing** (CPU-bound) | `ProcessPoolExecutor` | Parallel CPU computation for parsing |
| **Hybrid workflow** | `asyncio` + `ProcessPoolExecutor` | Async requests, then process pool for parsing |
| **Simple CPU tasks** | `ProcessPoolExecutor` | High-level interface, easier than `multiprocessing` |
| **Complex inter-process** | `multiprocessing` | More flexibility but slower than `ProcessPoolExecutor` |

**Key Insight**: Threading in Python cannot be used for parallel CPU computation due to the GIL, but it's perfect for I/O operations like web scraping because the processor sits idle waiting for data.

### 1.2 Async Pattern for I/O-bound Scrapers (Recommended)

```python
import asyncio
import aiohttp
from typing import List, Dict, Any

async def fetch_provider(session: aiohttp.ClientSession, url: str,
                         semaphore: asyncio.Semaphore) -> Dict[str, Any]:
    """Fetch single provider with concurrency control."""
    async with semaphore:  # Limit concurrent requests
        async with session.get(url) as response:
            return await response.json()

async def scrape_providers(urls: List[str], max_concurrent: int = 10) -> List[Dict[str, Any]]:
    """Scrape multiple providers asynchronously."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_provider(session, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out exceptions
    return [r for r in results if not isinstance(r, Exception)]

# Usage
urls = ["https://api.example.com/provider/1", "https://api.example.com/provider/2"]
results = asyncio.run(scrape_providers(urls, max_concurrent=10))
```

**Performance**: Asynchronous approaches can yield speed improvements of up to **10x** compared to synchronous methods.

### 1.3 ProcessPoolExecutor for CPU-bound Processing

```python
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Dict, Any
from pathlib import Path

def parse_html(html_content: str) -> Dict[str, Any]:
    """CPU-intensive HTML parsing (runs in separate process)."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    return {
        'npi': soup.select_one('.npi').text,
        'name': soup.select_one('.name').text,
        'specialty': soup.select_one('.specialty').text,
    }

def process_html_files(file_paths: List[Path], max_workers: int = 4) -> List[Dict[str, Any]]:
    """Process HTML files in parallel using separate processes."""
    results = []

    # Read HTML contents first (I/O in main process)
    html_contents = [p.read_text() for p in file_paths]

    # Parse in parallel processes (CPU-bound)
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(parse_html, html): html for html in html_contents}

        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"Error parsing HTML: {e}")

    return results
```

**Resource Limits**: Each process has its own memory space. For large datasets, limit workers to avoid memory exhaustion (see section 2.1).

### 1.4 Hybrid Pattern: Async Requests + Process Pool Parsing

```python
import asyncio
import aiohttp
from concurrent.futures import ProcessPoolExecutor
from typing import List, Dict, Any

async def fetch_and_parse(session: aiohttp.ClientSession,
                          url: str,
                          executor: ProcessPoolExecutor,
                          semaphore: asyncio.Semaphore) -> Dict[str, Any]:
    """Fetch HTML asynchronously, parse in separate process."""
    async with semaphore:
        async with session.get(url) as response:
            html = await response.text()

    # Offload CPU-bound parsing to process pool
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, parse_html, html)
    return result

async def scrape_and_parse(urls: List[str],
                           max_concurrent_requests: int = 10,
                           max_workers: int = 4) -> List[Dict[str, Any]]:
    """Combine async requests with process pool parsing."""
    semaphore = asyncio.Semaphore(max_concurrent_requests)

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        async with aiohttp.ClientSession() as session:
            tasks = [
                fetch_and_parse(session, url, executor, semaphore)
                for url in urls
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

    return [r for r in results if not isinstance(r, Exception)]
```

**Best Practice**: Write your scraper in asynchronous Python and distribute parsing through multiple processes.

---

## 2. Memory Management

### 2.1 Resource Limits by Scraper Type

Based on industry practices for parallel scraping:

| PC RAM | API Scrapers | Browser Scrapers | Anti-bot Scrapers |
|--------|-------------|------------------|-------------------|
| 8 GB   | 5-6         | 2                | 1                 |
| 16 GB  | 8-10        | 3-4              | 1-2               |
| 32 GB  | 15-20       | 6-8              | 2-3               |

**Memory Considerations**:
- Each process has its own memory space (no shared data)
- Large data structures duplicate across processes (high memory overhead)
- Browser automation (Selenium/Playwright) uses 500MB-1GB per instance
- Anti-bot solutions (stealth browsers) use 1-2GB per instance

### 2.2 Generator Pattern for Streaming (Memory-Efficient)

**Problem**: Loading entire datasets into memory causes OOM errors.

**Solution**: Use generators to yield one item at a time.

```python
from typing import Generator, Dict, Any
import json

def read_large_jsonl(file_path: str) -> Generator[Dict[str, Any], None, None]:
    """Stream JSONL file line by line (constant memory)."""
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def process_providers(input_file: str, output_file: str) -> None:
    """Process large file without loading all into memory."""
    with open(output_file, 'w') as out:
        for provider in read_large_jsonl(input_file):
            # Process one at a time
            normalized = normalize_provider(provider)
            out.write(json.dumps(normalized) + '\n')

# Memory usage: O(1) instead of O(n)
process_providers('raw/providers.jsonl', 'processed/providers.jsonl')
```

**Benefits**:
- Only one item in memory at a time
- Constant memory usage regardless of file size
- Automatic state management between executions

### 2.3 Generator Pipeline Pattern

```python
from typing import Generator, Dict, Any

def read_providers(file_path: str) -> Generator[Dict[str, Any], None, None]:
    """Stage 1: Read raw data."""
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                yield json.loads(line)

def filter_active(providers: Generator) -> Generator[Dict[str, Any], None, None]:
    """Stage 2: Filter active providers."""
    for provider in providers:
        if provider.get('accepting_new_patients'):
            yield provider

def normalize(providers: Generator) -> Generator[Dict[str, Any], None, None]:
    """Stage 3: Normalize data."""
    for provider in providers:
        yield {
            'npi': provider['npi'],
            'name': f"{provider['first_name']} {provider['last_name']}",
            'specialty': provider.get('specialty', 'Unknown'),
        }

# Chain generators into pipeline
pipeline = normalize(filter_active(read_providers('raw/providers.jsonl')))

# Process one at a time
for provider in pipeline:
    print(provider)  # Constant memory usage
```

**Key Advantage**: Each generator handles a specific transformation, data flows through one item at a time, minimizing memory.

### 2.4 Batch Writing to Reduce I/O Pressure

```python
from typing import List, Dict, Any
import json

def write_in_batches(items: List[Dict[str, Any]],
                     output_file: str,
                     batch_size: int = 1000) -> None:
    """Write to disk in batches (faster, more stable)."""
    with open(output_file, 'w') as f:
        batch = []
        for item in items:
            batch.append(item)

            if len(batch) >= batch_size:
                # Write batch
                for b in batch:
                    f.write(json.dumps(b) + '\n')
                batch = []

        # Write remaining
        for b in batch:
            f.write(json.dumps(b) + '\n')
```

**Best Practice**: Buffer 100-1000 items and write together. Faster than one-at-a-time, reduces I/O pressure.

### 2.5 Avoid Passing Large Data Between Processes

```python
from concurrent.futures import ProcessPoolExecutor
from typing import List

# BAD: Pass large data structure to each process
def process_bad(data: List[Dict], config: Dict) -> List[Dict]:
    with ProcessPoolExecutor(max_workers=4) as executor:
        # Config dict duplicated 4 times (memory waste)
        futures = [executor.submit(worker, item, config) for item in data]
        return [f.result() for f in futures]

# GOOD: Pass only necessary data
def process_good(data: List[Dict]) -> List[Dict]:
    with ProcessPoolExecutor(max_workers=4) as executor:
        # Each worker only gets one item
        futures = [executor.submit(worker_minimal, item) for item in data]
        return [f.result() for f in futures]
```

**Best Practice**: Use `multiprocessing.Manager` or shared memory if you must share large data structures.

---

## 3. Rate Limiting

### 3.1 Industry Standards

**Respectful Scraping Rate**: 10-30 requests/second is widely considered respectful to web servers.

**Common Rate Limiting Types**:
- Requests per second (5, 10, 60 RPS)
- Concurrent requests (10-50 in-flight)
- Token buckets (tokens refill over time)
- Leaky buckets (total requests per time period)

### 3.2 Semaphore-based Concurrency Limiting (Built-in)

```python
import asyncio
import aiohttp

async def fetch_with_limit(session: aiohttp.ClientSession,
                           url: str,
                           semaphore: asyncio.Semaphore) -> dict:
    """Limit concurrent requests using semaphore."""
    async with semaphore:  # Only N tasks can enter simultaneously
        async with session.get(url) as response:
            return await response.json()

async def scrape_limited(urls: list, max_concurrent: int = 10) -> list:
    """Hard cap on parallel executions."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_with_limit(session, url, semaphore) for url in urls]
        return await asyncio.gather(*tasks)

# Only 10 requests in-flight at any time
asyncio.run(scrape_limited(urls, max_concurrent=10))
```

### 3.3 TCPConnector for Per-Domain Limiting

```python
import aiohttp

async def scrape_multiple_domains(urls: list) -> list:
    """Different limits per domain."""
    connector = aiohttp.TCPConnector(
        limit=100,              # Total concurrent connections
        limit_per_host=10,      # Max 10 per domain
    )

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [session.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return [await r.json() for r in responses]
```

**Advantage over Semaphore**: Can limit total calls AND per-domain independently.

### 3.4 Time-based Rate Limiting (Leaky Bucket)

```python
import asyncio
from collections import defaultdict
from typing import Dict

class RateLimiter:
    """Domain-specific rate limiter using leaky bucket algorithm."""

    def __init__(self, requests_per_second: float):
        self.rps = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request: Dict[str, float] = defaultdict(float)
        self.locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def acquire(self, domain: str) -> None:
        """Wait until request is allowed for this domain."""
        async with self.locks[domain]:
            now = asyncio.get_event_loop().time()
            time_since_last = now - self.last_request[domain]

            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                await asyncio.sleep(wait_time)

            self.last_request[domain] = asyncio.get_event_loop().time()

# Usage
limiter = RateLimiter(requests_per_second=10)

async def fetch_with_rate_limit(session, url, limiter):
    domain = url.split('/')[2]  # Extract domain
    await limiter.acquire(domain)

    async with session.get(url) as response:
        return await response.json()
```

### 3.5 Global Rate Limiting with asyncio.Queue

```python
import asyncio
from typing import List

async def worker(queue: asyncio.Queue,
                session: aiohttp.ClientSession,
                results: List) -> None:
    """Worker that processes URLs from queue."""
    while True:
        url = await queue.get()
        if url is None:  # Poison pill
            break

        try:
            async with session.get(url) as response:
                data = await response.json()
                results.append(data)
        except Exception as e:
            print(f"Error fetching {url}: {e}")
        finally:
            queue.task_done()

async def scrape_with_queue(urls: List[str], num_workers: int = 10) -> List:
    """Global concurrency control using queue + workers."""
    queue = asyncio.Queue(maxsize=num_workers)  # Limit queue size
    results = []

    async with aiohttp.ClientSession() as session:
        # Start workers
        workers = [
            asyncio.create_task(worker(queue, session, results))
            for _ in range(num_workers)
        ]

        # Feed queue
        for url in urls:
            await queue.put(url)

        # Wait for completion
        await queue.join()

        # Stop workers
        for _ in range(num_workers):
            await queue.put(None)

        await asyncio.gather(*workers)

    return results
```

**Advantage**: Queue maxsize limits in-flight requests globally across all workers.

### 3.6 Using aiolimiter (Minimal Dependency)

```python
from aiolimiter import AsyncLimiter
import aiohttp

async def scrape_with_aiolimiter(urls: list) -> list:
    """Use aiolimiter for precise rate limiting."""
    # Allow 10 requests per second
    limiter = AsyncLimiter(max_rate=10, time_period=1)

    async with aiohttp.ClientSession() as session:
        results = []
        for url in urls:
            async with limiter:
                async with session.get(url) as response:
                    results.append(await response.json())
        return results
```

**Installation**: `pip install aiolimiter`

---

## 4. Error Recovery

### 4.1 Checkpoint/Resume Pattern

**Problem**: Scraper crashes mid-run, loses all progress.

**Solution**: Save progress periodically, resume from last checkpoint.

```python
import json
from pathlib import Path
from typing import Set

def save_checkpoint(completed_ids: Set[str], checkpoint_file: str) -> None:
    """Save completed IDs to disk."""
    with open(checkpoint_file, 'w') as f:
        json.dump(list(completed_ids), f)

def load_checkpoint(checkpoint_file: str) -> Set[str]:
    """Load previously completed IDs."""
    path = Path(checkpoint_file)
    if path.exists():
        with open(path, 'r') as f:
            return set(json.load(f))
    return set()

def scrape_with_checkpoints(provider_ids: list, checkpoint_file: str) -> None:
    """Resume from checkpoint if interrupted."""
    completed = load_checkpoint(checkpoint_file)

    # Skip already completed
    remaining = [pid for pid in provider_ids if pid not in completed]
    print(f"Resuming: {len(remaining)} remaining out of {len(provider_ids)}")

    for pid in remaining:
        try:
            data = fetch_provider(pid)
            save_to_disk(data)
            completed.add(pid)

            # Save checkpoint every 100 providers
            if len(completed) % 100 == 0:
                save_checkpoint(completed, checkpoint_file)
        except Exception as e:
            print(f"Error fetching {pid}: {e}")
            continue

    # Final checkpoint
    save_checkpoint(completed, checkpoint_file)
```

**Best Practice**: Flush checkpoints every 500-5000 records. Ensure idempotency to prevent duplicates on resume.

### 4.2 Exponential Backoff with Jitter

```python
import asyncio
import random
from typing import Optional

async def fetch_with_retry(session: aiohttp.ClientSession,
                           url: str,
                           max_retries: int = 5) -> Optional[dict]:
    """Retry with exponential backoff and jitter."""
    for attempt in range(max_retries):
        try:
            async with session.get(url) as response:
                if response.status == 429:  # Rate limited
                    # Exponential backoff: 2^attempt + random jitter
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"Rate limited, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    continue

                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientError as e:
            if attempt == max_retries - 1:
                print(f"Failed after {max_retries} attempts: {e}")
                return None

            # Exponential backoff with jitter
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            await asyncio.sleep(wait_time)

    return None
```

**Jitter Benefits**: Reduces collision chances when multiple scrapers retry simultaneously.

### 4.3 Circuit Breaker Pattern (Stdlib Implementation)

```python
import time
from typing import Callable, Any
from functools import wraps

class CircuitBreaker:
    """Circuit breaker pattern using stdlib only."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function with circuit breaker protection."""
        if self.state == 'open':
            if time.time() - self.last_failure_time > self.timeout:
                # Try recovery
                self.state = 'half-open'
                print("Circuit breaker: trying recovery (half-open)")
            else:
                raise Exception("Circuit breaker is OPEN (service unavailable)")

        try:
            result = func(*args, **kwargs)

            # Success: reset if in half-open state
            if self.state == 'half-open':
                print("Circuit breaker: recovered (closing)")
                self.state = 'closed'
                self.failures = 0

            return result

        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()

            if self.failures >= self.failure_threshold:
                self.state = 'open'
                print(f"Circuit breaker: OPENED after {self.failures} failures")

            raise e

# Usage
breaker = CircuitBreaker(failure_threshold=5, timeout=60)

def fetch_provider(provider_id: str) -> dict:
    # Make API call
    response = requests.get(f"https://api.example.com/provider/{provider_id}")
    response.raise_for_status()
    return response.json()

# Wrap function calls
for pid in provider_ids:
    try:
        data = breaker.call(fetch_provider, pid)
        process(data)
    except Exception as e:
        print(f"Skipping {pid}: {e}")
```

**Alternative**: Use `pybreaker` library (`pip install pybreaker`) for decorator-based approach.

### 4.4 Circuit Breaker with Async Support

```python
import asyncio
import time
from typing import Callable, Any

class AsyncCircuitBreaker:
    """Async circuit breaker for asyncio code."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = 'closed'

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call async function with circuit breaker."""
        if self.state == 'open':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'half-open'
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)

            if self.state == 'half-open':
                self.state = 'closed'
                self.failures = 0

            return result

        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()

            if self.failures >= self.failure_threshold:
                self.state = 'open'

            raise e

# Usage
breaker = AsyncCircuitBreaker(failure_threshold=5, timeout=60)

async def fetch_provider_async(session, provider_id):
    async with session.get(f"https://api.example.com/provider/{provider_id}") as response:
        return await response.json()

# Protect async calls
for pid in provider_ids:
    try:
        data = await breaker.call(fetch_provider_async, session, pid)
    except Exception as e:
        print(f"Skipping {pid}: {e}")
```

---

## 5. Monitoring at Scale

### 5.1 Metric Types

| Metric Type | Description | Example |
|-------------|-------------|---------|
| **Counter** | Starts at 0, increases | Total requests, total errors |
| **Gauge** | Can go up/down | Active workers, memory usage |
| **Histogram** | Sample observations | Request duration, response size |

**Best Practice**: Collect metrics every 10-30 seconds for most applications. Critical services: 1-5 seconds. Background jobs: less frequent.

### 5.2 Simple Metrics Collection (Stdlib)

```python
import time
from collections import defaultdict
from typing import Dict, Any

class MetricsCollector:
    """Simple metrics collector using stdlib."""

    def __init__(self):
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, list] = defaultdict(list)
        self.start_time = time.time()

    def increment(self, name: str, value: int = 1) -> None:
        """Increment counter."""
        self.counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        """Set gauge value."""
        self.gauges[name] = value

    def record_histogram(self, name: str, value: float) -> None:
        """Record histogram observation."""
        self.histograms[name].append(value)

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        runtime = time.time() - self.start_time

        return {
            'runtime_seconds': runtime,
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'histograms': {
                name: {
                    'count': len(values),
                    'mean': sum(values) / len(values) if values else 0,
                    'min': min(values) if values else 0,
                    'max': max(values) if values else 0,
                }
                for name, values in self.histograms.items()
            }
        }

# Usage
metrics = MetricsCollector()

async def fetch_with_metrics(session, url):
    start = time.time()
    try:
        async with session.get(url) as response:
            metrics.increment('requests_total')
            metrics.record_histogram('request_duration', time.time() - start)

            if response.status == 200:
                metrics.increment('requests_success')
            else:
                metrics.increment('requests_failed')

            return await response.json()
    except Exception as e:
        metrics.increment('requests_error')
        raise

# Print summary
print(json.dumps(metrics.get_summary(), indent=2))
```

### 5.3 Progress Tracking for Multiple Scrapers

```python
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

class ProgressTracker:
    """Track progress across multiple scrapers."""

    def __init__(self, project_name: str, output_dir: str):
        self.project_name = project_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.progress_file = self.output_dir / 'progress.json'
        self.start_time = datetime.now()

        self.progress = {
            'project': project_name,
            'started_at': self.start_time.isoformat(),
            'phase': None,
            'total_items': 0,
            'completed_items': 0,
            'failed_items': 0,
            'errors': [],
        }

    def set_phase(self, phase: str, total_items: int) -> None:
        """Set current phase and total items."""
        self.progress['phase'] = phase
        self.progress['total_items'] = total_items
        self.progress['completed_items'] = 0
        self.save()

    def increment(self, count: int = 1) -> None:
        """Increment completed count."""
        self.progress['completed_items'] += count
        self.save()

    def add_error(self, error: str) -> None:
        """Record error."""
        self.progress['failed_items'] += 1
        self.progress['errors'].append({
            'timestamp': datetime.now().isoformat(),
            'error': str(error),
        })
        self.save()

    def save(self) -> None:
        """Save progress to disk."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        completed = self.progress['completed_items']
        total = self.progress['total_items']

        # Calculate rate and ETA
        if completed > 0:
            rate = completed / elapsed
            remaining = total - completed
            eta_seconds = remaining / rate if rate > 0 else 0
        else:
            rate = 0
            eta_seconds = 0

        self.progress['elapsed_seconds'] = elapsed
        self.progress['rate_per_second'] = rate
        self.progress['eta_seconds'] = eta_seconds
        self.progress['percent_complete'] = (completed / total * 100) if total > 0 else 0

        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)

# Usage
tracker = ProgressTracker('audiobee_bcbs_il', '20251210')

# Phase 1
tracker.set_phase('search', total_items=100)
for i in range(100):
    try:
        result = search_providers(i)
        tracker.increment()
    except Exception as e:
        tracker.add_error(e)
```

### 5.4 Monitoring Dashboard (Simple Text-based)

```python
import json
from pathlib import Path
from typing import List, Dict

def generate_monitoring_dashboard(project_dirs: List[str]) -> str:
    """Generate simple text dashboard for multiple scrapers."""
    dashboard = []
    dashboard.append("=" * 80)
    dashboard.append("SCRAPER MONITORING DASHBOARD")
    dashboard.append("=" * 80)

    for project_dir in project_dirs:
        progress_file = Path(project_dir) / 'progress.json'

        if not progress_file.exists():
            continue

        with open(progress_file, 'r') as f:
            progress = json.load(f)

        project = progress['project']
        phase = progress.get('phase', 'unknown')
        completed = progress.get('completed_items', 0)
        total = progress.get('total_items', 0)
        percent = progress.get('percent_complete', 0)
        rate = progress.get('rate_per_second', 0)
        eta = progress.get('eta_seconds', 0)
        failed = progress.get('failed_items', 0)

        dashboard.append(f"\n{project} - {phase}")
        dashboard.append(f"  Progress: {completed}/{total} ({percent:.1f}%)")
        dashboard.append(f"  Rate: {rate:.2f} items/sec")
        dashboard.append(f"  ETA: {eta/60:.1f} minutes")
        dashboard.append(f"  Failed: {failed}")

    dashboard.append("\n" + "=" * 80)
    return "\n".join(dashboard)

# Usage
projects = [
    'audiobee_bcbs_il/20251210',
    'audiobee_florida_blue/20251210',
    'audiobee_multiplan/20251210',
]

print(generate_monitoring_dashboard(projects))
```

### 5.5 Alerting on Failures (Simple Email)

```python
import smtplib
from email.mime.text import MIMEText
from typing import List

def send_alert(subject: str, message: str, recipients: List[str]) -> None:
    """Send email alert using stdlib smtplib."""
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = 'scraper-alerts@example.com'
    msg['To'] = ', '.join(recipients)

    # Use environment variables for credentials
    import os
    smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER')
    smtp_pass = os.getenv('SMTP_PASS')

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)

# Usage in error handler
def monitor_scraper_health(tracker: ProgressTracker) -> None:
    """Monitor scraper health and alert on issues."""
    error_count = tracker.progress['failed_items']
    total_count = tracker.progress['completed_items'] + error_count

    # Alert if error rate > 10%
    if total_count > 100 and error_count / total_count > 0.1:
        send_alert(
            subject=f"High Error Rate: {tracker.project_name}",
            message=f"Error rate: {error_count}/{total_count} ({error_count/total_count*100:.1f}%)",
            recipients=['team@example.com']
        )
```

---

## 6. Complete Example: Scalable Scraper

```python
"""
Complete example combining all best practices:
- Async I/O for requests
- ProcessPoolExecutor for parsing
- Generator pattern for memory efficiency
- Rate limiting with semaphore
- Circuit breaker for error recovery
- Checkpointing for resume
- Metrics collection
"""

import asyncio
import aiohttp
import json
import time
from pathlib import Path
from typing import List, Dict, Set, Generator
from concurrent.futures import ProcessPoolExecutor

# Configuration
MAX_CONCURRENT_REQUESTS = 10
MAX_PARSING_WORKERS = 4
REQUESTS_PER_SECOND = 10
CHECKPOINT_INTERVAL = 100

class ScalableScraper:
    """Production-ready scraper with best practices."""

    def __init__(self, project_name: str, output_dir: str):
        self.project_name = project_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Metrics
        self.metrics = MetricsCollector()

        # Progress tracking
        self.tracker = ProgressTracker(project_name, str(self.output_dir))

        # Circuit breaker
        self.breaker = AsyncCircuitBreaker(failure_threshold=5, timeout=60)

        # Checkpointing
        self.checkpoint_file = self.output_dir / 'checkpoint.json'
        self.completed_ids = self.load_checkpoint()

    def load_checkpoint(self) -> Set[str]:
        """Load checkpoint from disk."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                return set(json.load(f))
        return set()

    def save_checkpoint(self) -> None:
        """Save checkpoint to disk."""
        with open(self.checkpoint_file, 'w') as f:
            json.dump(list(self.completed_ids), f)

    async def fetch_provider(self, session: aiohttp.ClientSession,
                            provider_id: str,
                            semaphore: asyncio.Semaphore) -> Dict:
        """Fetch provider with rate limiting and circuit breaker."""
        async with semaphore:
            try:
                result = await self.breaker.call(
                    self._do_fetch, session, provider_id
                )
                self.metrics.increment('requests_success')
                return result
            except Exception as e:
                self.metrics.increment('requests_failed')
                self.tracker.add_error(str(e))
                return None

    async def _do_fetch(self, session: aiohttp.ClientSession,
                       provider_id: str) -> Dict:
        """Actual fetch implementation."""
        start = time.time()

        url = f"https://api.example.com/provider/{provider_id}"
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()

            self.metrics.record_histogram('request_duration', time.time() - start)
            return data

    async def scrape_phase_1(self, provider_ids: List[str]) -> None:
        """Phase 1: Fetch provider data."""
        # Skip already completed
        remaining = [pid for pid in provider_ids if pid not in self.completed_ids]
        self.tracker.set_phase('fetch', total_items=len(remaining))

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        async with aiohttp.ClientSession() as session:
            for i, provider_id in enumerate(remaining):
                data = await self.fetch_provider(session, provider_id, semaphore)

                if data:
                    # Save raw data
                    raw_file = self.output_dir / 'raw' / f'{provider_id}.json'
                    raw_file.parent.mkdir(exist_ok=True)
                    with open(raw_file, 'w') as f:
                        json.dump(data, f)

                    self.completed_ids.add(provider_id)
                    self.tracker.increment()

                # Checkpoint periodically
                if (i + 1) % CHECKPOINT_INTERVAL == 0:
                    self.save_checkpoint()

        # Final checkpoint
        self.save_checkpoint()

    def parse_phase_2(self) -> None:
        """Phase 2: Parse HTML in parallel processes."""
        raw_files = list((self.output_dir / 'raw').glob('*.json'))
        self.tracker.set_phase('parse', total_items=len(raw_files))

        with ProcessPoolExecutor(max_workers=MAX_PARSING_WORKERS) as executor:
            futures = {
                executor.submit(self.parse_provider, f): f
                for f in raw_files
            }

            for future in as_completed(futures):
                try:
                    result = future.result()

                    # Save parsed data
                    parsed_file = self.output_dir / 'parsed' / f'{result["npi"]}.json'
                    parsed_file.parent.mkdir(exist_ok=True)
                    with open(parsed_file, 'w') as f:
                        json.dump(result, f)

                    self.tracker.increment()
                except Exception as e:
                    self.tracker.add_error(str(e))

    @staticmethod
    def parse_provider(file_path: Path) -> Dict:
        """Parse provider data (runs in separate process)."""
        with open(file_path, 'r') as f:
            data = json.load(f)

        # CPU-intensive parsing logic
        return {
            'npi': data['npi'],
            'name': f"{data['first_name']} {data['last_name']}",
            'specialty': data.get('specialty', 'Unknown'),
        }

    def normalize_phase_3(self) -> None:
        """Phase 3: Normalize using generator pattern."""
        parsed_files = list((self.output_dir / 'parsed').glob('*.json'))
        self.tracker.set_phase('normalize', total_items=len(parsed_files))

        output_file = self.output_dir / 'final_output.jsonl'

        with open(output_file, 'w') as out:
            for provider in self.read_parsed_providers():
                normalized = self.normalize_provider(provider)
                out.write(json.dumps(normalized) + '\n')
                self.tracker.increment()

    def read_parsed_providers(self) -> Generator[Dict, None, None]:
        """Generator: stream providers without loading all to memory."""
        for file_path in (self.output_dir / 'parsed').glob('*.json'):
            with open(file_path, 'r') as f:
                yield json.load(f)

    @staticmethod
    def normalize_provider(provider: Dict) -> Dict:
        """Normalize provider data."""
        return {
            'npi': provider['npi'],
            'name': provider['name'],
            'specialty': provider['specialty'],
        }

    async def run(self, provider_ids: List[str]) -> None:
        """Run complete scraping pipeline."""
        print(f"Starting scraper: {self.project_name}")

        # Phase 1: Fetch
        await self.scrape_phase_1(provider_ids)

        # Phase 2: Parse
        self.parse_phase_2()

        # Phase 3: Normalize
        self.normalize_phase_3()

        # Print metrics
        print(json.dumps(self.metrics.get_summary(), indent=2))
        print(f"Completed: {self.project_name}")

# Usage
async def main():
    provider_ids = [f"provider_{i}" for i in range(1000)]

    scraper = ScalableScraper(
        project_name='audiobee_bcbs_il',
        output_dir='20251210'
    )

    await scraper.run(provider_ids)

if __name__ == '__main__':
    asyncio.run(main())
```

---

## 7. Key Takeaways

### Architecture Decisions

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| **I/O-bound work** | `asyncio` + `aiohttp` | 10x faster, non-blocking I/O |
| **CPU-bound work** | `ProcessPoolExecutor` | True parallelism (bypasses GIL) |
| **Memory optimization** | Generator patterns | O(1) memory instead of O(n) |
| **Rate limiting** | Semaphore + leaky bucket | Built-in + domain-specific control |
| **Error recovery** | Circuit breaker + exponential backoff | Prevents cascading failures |
| **Monitoring** | Counters/gauges/histograms | Production visibility |
| **Checkpointing** | Save every 100-1000 records | Resume on failure |

### Resource Planning for 100+ Scrapers

| Resource | API Scrapers | Browser Scrapers | Anti-bot Scrapers |
|----------|-------------|------------------|-------------------|
| **Memory (16GB PC)** | 8-10 parallel | 3-4 parallel | 1-2 parallel |
| **Concurrency** | 10-30 async requests | 2-4 browsers | 1-2 browsers |
| **Rate Limit** | 10-30 RPS | 5-10 RPS | 1-5 RPS |
| **Checkpoint Interval** | Every 1000 records | Every 100 records | Every 50 records |

### Anti-Patterns to Avoid

1. **Loading entire datasets to memory** → Use generators
2. **No rate limiting** → Use semaphores + domain-specific limits
3. **No checkpointing** → Save progress periodically
4. **Ignoring circuit breakers** → Wrap external calls
5. **No monitoring** → Track metrics for production visibility
6. **Passing large data between processes** → Minimize inter-process data transfer
7. **Using threads for CPU work** → Use processes instead

---

## 8. Sources

### Parallel Execution & Concurrency
- [Advanced Web Scraping With Python Tactics in 2025](https://oxylabs.io/blog/advanced-web-scraping-python)
- [The Ultimate Guide to Scalable Web Scraping in 2025](https://dev.to/wisdomudo/the-ultimate-guide-to-scalable-web-scraping-in-2025-tools-proxies-and-automation-workflows-4j6l)
- [Web Scraping Speed: Processes, Threads and Async](https://scrapfly.io/blog/posts/web-scraping-speed)
- [Multithreading vs. Multiprocessing in Python](https://thenewstack.io/python-threadpool-vs-multiprocessing/)
- [Speed Up Your Python Program With Concurrency – Real Python](https://realpython.com/python-concurrency/)

### Memory Management
- [Advanced Python Generator Patterns](https://dhirendrabiswal.com/advanced-python-generator-patterns-coroutines-async-generators-memory-efficient-data-streaming/)
- [Python JSON Streaming: Handle Large Datasets Efficiently](https://pytutorial.com/python-json-streaming-handle-large-datasets-efficiently/)
- [Harnessing Python Generators for Efficient Data Streaming](https://dev.to/freelancingsolutions/harnessing-python-generators-for-efficient-data-streaming-in-stock-apis-1gpm)

### Rate Limiting
- [How to Rate Limit Async Requests in Python](https://scrapfly.io/blog/posts/how-to-rate-limit-asynchronous-python-requests)
- [Effective Strategies for Rate Limiting Asynchronous Requests in Python](https://proxiesapi.com/articles/effective-strategies-for-rate-limiting-asynchronous-requests-in-python)
- [AsyncIO Rate Limiter for Python](https://asynciolimiter.readthedocs.io/)
- [Python aiohttp rate limit](https://copdips.com/2023/01/python-aiohttp-rate-limit.html)

### Error Recovery
- [Automatic Failover Strategies for Reliable Data Extraction](https://scrapfly.io/blog/posts/automatic-failover-strategies-for-reliable-data-extraction)
- [Exception Handling Strategies for Robust Web Scraping](https://scrapingant.com/blog/python-exception-handling)
- [Circuit Breaker Pattern - PyBreaker](https://github.com/danielfm/pybreaker)
- [Python Circuit Breaker Implementation](https://github.com/fabfuel/circuitbreaker)

### Monitoring
- [How to Monitor Your Scrapy Spiders - ScrapeOps](https://scrapeops.io/python-scrapy-playbook/how-to-monitor-scrapy-spiders/)
- [Understanding metrics and monitoring with Python](https://opensource.com/article/18/4/metrics-monitoring-and-python)
- [Python Performance Monitoring](https://signoz.io/guides/python-performance-monitoring/)

### General Best Practices
- [Large-Scale Web Scraping: Techniques & Challenges](https://research.aimultiple.com/large-scale-web-scraping/)
- [6 Key Steps to Large Scale Web Scraping](https://scrape.do/blog/large-scale-web-scraping/)
- [Best Practices for Web Scraping in 2025](https://www.scraperapi.com/web-scraping/best-practices/)
- [Optimizing Web Scraping Speed in Python](https://scrapingant.com/blog/fast-web-scraping-python)
