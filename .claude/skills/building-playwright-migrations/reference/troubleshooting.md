# Troubleshooting Migration Failures

Common issues when building Playwright migrations and how to resolve them.

## Selector Issues

### Problem: "Element not found" or timeout errors

**Symptoms**:

```
TimeoutError: page.locator(selector).click: Timeout 30000ms exceeded
```

**Diagnosis**:

1. Check if element is in an iframe
2. Verify selector in browser DevTools
3. Check if element loads dynamically

**Solutions**:

```python
# Add explicit wait
await page.wait_for_selector(selector, state="visible", timeout=10000)

# Check for iframe
frame = await get_editor_iframe(page)
if frame:
    await frame.locator(selector).click()
else:
    await page.locator(selector).click()

# Use multiple fallback selectors
selectors = ["#primary", ".fallback", "[data-testid='alternative']"]
for sel in selectors:
    try:
        await page.locator(sel).click(timeout=3000)
        break
    except:
        continue
```

### Problem: Selector works locally but fails in production

**Cause**: Different Playwright versions, browser differences, or timing issues

**Solution**:

```python
# Add network idle wait
await page.wait_for_load_state("networkidle")

# Wait for specific API call
await page.wait_for_response(lambda r: "/api/template" in r.url)

# Use stable selectors
await page.get_by_role("button", name="Save")  # Better than CSS selector
```

## Iframe Issues

### Problem: Cannot access template editor

**Symptoms**:

```
content_frame is None
```

**Diagnosis**:

```python
# Check if iframe exists
iframe_count = await page.locator("iframe").count()
logger.info(f"Found {iframe_count} iframes")

# List all iframe IDs
frames = await page.frames()
for frame in frames:
    logger.info(f"Frame: {frame.url}")
```

**Solutions**:

```python
# Try multiple iframe selectors
async def get_editor_iframe_robust(page):
    selectors = [
        "#editingZone iframe",
        "iframe[id*='edit']",
        "iframe[src*='template']",
        "iframe"  # Last resort: first iframe
    ]

    for selector in selectors:
        try:
            iframe = await page.locator(selector).first.element_handle(timeout=3000)
            if iframe:
                frame = await iframe.content_frame()
                if frame:
                    logger.info(f"Found iframe with: {selector}")
                    return frame
        except:
            continue

    return None
```

## Network/API Issues

### Problem: API requests fail during migration

**Symptoms**:

```
Failed to create flow: 401 Unauthorized
```

**Diagnosis**:

```python
# Log all network requests
page.on("request", lambda req: logger.info(f"Request: {req.method} {req.url}"))
page.on("response", lambda res: logger.info(f"Response: {res.status} {res.url}"))
```

**Solutions**:

```python
# Use backend API proxy for OAuth-protected endpoints
from beenanativeapp.services.playwright.custom_functions.mailchimp_to_klaviyo_components.automation_flow.klaviyo_apis.backend_klaviyo_client import BackendKlaviyoClient

client = BackendKlaviyoClient(logger)
response = await client.create_flow(flow_data)  # Handles auth automatically
```

### Problem: Rate limiting errors

**Symptoms**:

```
429 Too Many Requests
```

**Solutions**:

```python
import asyncio

# Add delays between requests
for item in items:
    await process_item(item)
    await asyncio.sleep(1)  # 1 second delay

# Implement exponential backoff
async def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if "429" in str(e) or "rate limit" in str(e).lower():
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"Rate limited, waiting {wait_time}s")
                await asyncio.sleep(wait_time)
            else:
                raise
    raise Exception("Max retries exceeded")
```

## Data Extraction Issues

### Problem: Extracted data is incomplete or malformed

**Diagnosis**:

```python
# Log extracted data at each step
logger.info(f"Extracted {len(items)} items")
for item in items:
    logger.debug(f"Item: {json.dumps(item, indent=2)}")
```

**Solutions**:

```python
# Add validation
def validate_extracted_data(data):
    required_fields = ["type", "content"]

    for field in required_fields:
        if field not in data:
            logger.warning(f"Missing field: {field}")
            return False

    return True

# Use before adding to mapped_contents
if validate_extracted_data(item):
    mapped_contents.append(item)
else:
    logger.warning(f"Skipping invalid item: {item}")
```

### Problem: Styles not preserved after migration

**Cause**: Style extraction incomplete or destination platform doesn't support certain styles

**Solutions**:

```python
# Extract all inline styles
style_attr = await element.get_attribute("style") or ""

# Parse thoroughly
styles = {}
for rule in style_attr.split(";"):
    if ":" in rule:
        prop, value = rule.split(":", 1)
        styles[prop.strip()] = value.strip()

# Also check computed styles
computed = await element.evaluate("""
    el => {
        const computed = window.getComputedStyle(el);
        return {
            backgroundColor: computed.backgroundColor,
            color: computed.color,
            fontSize: computed.fontSize,
            padding: computed.padding
        };
    }
""")
```

## Memory Issues

### Problem: Script crashes with "Out of memory"

**Cause**: Too many open pages or browser contexts

**Solutions**:

```python
# Close pages after use
klaviyo_page = await page.context.new_page()
try:
    await klaviyo_page.goto("https://www.klaviyo.com/templates")
    # ... operations
finally:
    await klaviyo_page.close()  # Always close

# Limit concurrent operations
from asyncio import Semaphore

sem = Semaphore(3)  # Max 3 concurrent

async def process_with_limit(item):
    async with sem:
        return await process_item(item)

results = await asyncio.gather(*[process_with_limit(item) for item in items])
```

## Platform-Specific Issues

### Mailchimp

**Problem**: Template editor loads but content is empty

**Solution**:

```python
# Wait for content to load
await page.wait_for_function("""
    () => {
        const iframe = document.querySelector('#editingZone iframe');
        if (!iframe) return false;
        const doc = iframe.contentDocument;
        return doc && doc.querySelectorAll('td.mceColumn').length > 0;
    }
""", timeout=15000)
```

### Klaviyo

**Problem**: Template blocks added in wrong order

**Cause**: Klaviyo builds templates from bottom to top

**Solution**:

```python
# Reverse the content array
for item in reversed(mapped_contents):
    await add_block_to_klaviyo(page, item)
```

### Yotpo

**Problem**: Authentication state lost during migration

**Solution**:

```python
# Store cookies and restore
cookies = await page.context.cookies()
# ... perform operations

# Restore if needed
await page.context.add_cookies(cookies)
```

## Debugging Techniques

### Enable verbose logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Take screenshots at each step

```python
step_counter = 0

async def screenshot_step(page, description):
    global step_counter
    step_counter += 1
    await page.screenshot(path=f"debug/step_{step_counter}_{description}.png")
    logger.info(f"Screenshot saved: step_{step_counter}_{description}.png")

# Use in migration
await screenshot_step(page, "after_template_load")
# ... extraction code
await screenshot_step(page, "after_extraction")
```

### Slow down execution for debugging

```python
from playwright.async_api import async_playwright

# Launch with slow_mo
browser = await playwright.chromium.launch(slow_mo=1000)  # 1 second delay
```

### Interactive debugging

```python
# Pause execution to inspect manually
await page.pause()  # Opens Playwright Inspector
```

## When to Use UI vs API Approach

**Use UI automation when**:

- Platform doesn't provide public API
- API is rate-limited
- Need to preserve exact visual appearance
- Testing user workflows

**Use API approach when**:

- Platform has stable, documented API
- Need high performance/bulk operations
- UI changes frequently
- Complex data transformations needed

**Hybrid approach** (recommended):

- Extract via UI (selectors for data)
- Transform programmatically
- Create via API (more reliable)

## Getting Help

1. Check existing migrations in `custom_functions/` for similar patterns
2. Review platform's DOM structure in browser DevTools
3. Test selectors in browser console before adding to code
4. Add comprehensive logging to identify exact failure point
5. Check platform's developer documentation for API alternatives
