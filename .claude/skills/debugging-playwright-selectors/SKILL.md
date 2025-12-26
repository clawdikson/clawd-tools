---
name: debugging-playwright-selectors
description: Troubleshoot Playwright selector failures in ESP platform automation. Covers iframe handling, dynamic content, timing issues, and fallback strategies. Use when automation scripts fail with timeout or element-not-found errors.
---

# Debugging Playwright Selectors

Debug and fix selector issues in Playwright automation scripts for ESP platforms. This skill focuses on practical debugging techniques specific to the Beena Native App's migration workflows.

## When to Use This Skill

- Automation jobs fail with "Timeout" or "Element not found" errors
- Selectors work in development but fail in production
- Platform UI updates break existing automation
- Need to make selectors more robust and reliable

## Quick Diagnosis Checklist

Run through this checklist when a selector fails:

1. **Is the element in an iframe?** → 80% of ESP selector issues
2. **Is the element loaded dynamically?** → Add wait strategies
3. **Has the platform UI changed?** → Update selector or add fallbacks
4. **Is it a timing issue?** → Increase timeout or add explicit waits
5. **Is the selector too specific?** → Use more flexible selectors

## Common Failure Patterns

### Pattern 1: Iframe Not Handled

**Error**:

```
TimeoutError: page.locator("#saveButton").click: Timeout 30000ms exceeded
```

**Diagnosis**:

```python
# Check for iframes
iframe_count = await page.locator("iframe").count()
logger.info(f"Page has {iframe_count} iframes")

# List all frames
for frame in page.frames():
    logger.info(f"Frame URL: {frame.url}")
```

**Fix**:

```python
# Get iframe first
iframe = await page.locator("#editingZone iframe").element_handle()
content_frame = await iframe.content_frame()

# Then access elements within iframe
await content_frame.locator("#saveButton").click()
```

**Project-specific pattern**:

- Mailchimp: Uses `#editingZone iframe` for template editor
- Klaviyo: Template builder is in main page, no iframe
- Yotpo: Campaign editor uses iframe for preview

### Pattern 2: Dynamic Content Not Loaded

**Error**:

```
Element is not visible
```

**Diagnosis**:

```python
# Check if element exists but not visible
count = await page.locator(selector).count()
is_visible = await page.locator(selector).is_visible() if count > 0 else False

logger.info(f"Element count: {count}, Visible: {is_visible}")
```

**Fix**:

```python
# Wait for network idle (SPA content loaded)
await page.wait_for_load_state("networkidle")

# Wait for specific element to be visible
await page.locator(selector).wait_for(state="visible", timeout=10000)

# Or wait for API response
await page.wait_for_response(lambda r: "/api/campaigns" in r.url)
```

### Pattern 3: Selector Too Brittle

**Error**:

```
Selector "#content-block-123" resolved to 0 elements
```

**Cause**: ID changes dynamically or platform updated HTML structure

**Fix - Use flexible selectors**:

```python
# ❌ Brittle: IDs change
await page.locator("#content-block-123").click()

# ✅ Better: Class-based
await page.locator(".content-block").first.click()

# ✅ Best: Role-based (most stable)
await page.get_by_role("button", name="Save").click()

# ✅ Best: Text-based for unique content
await page.get_by_text("Create Campaign", exact=False).click()
```

### Pattern 4: Multiple Elements Match

**Error**:

```
strict mode violation: locator(".button") resolved to 5 elements
```

**Fix**:

```python
# Use .first or .nth()
await page.locator(".button").first.click()

# Or use more specific selector
await page.locator(".campaign-list .button").first.click()

# Or filter by text
await page.get_by_role("button").filter(has_text="Save").click()
```

## Interactive Debugging Techniques

### Technique 1: Pause Execution

```python
# Open Playwright Inspector
await page.pause()

# Inspector allows:
# - Inspect DOM in real-time
# - Test selectors
# - Step through actions
# - Record new actions
```

### Technique 2: Visual Debugging

```python
# Take screenshots at failure points
try:
    await page.locator(selector).click()
except Exception as e:
    await page.screenshot(path=f"debug/failure_{selector}.png")
    logger.error(f"Selector failed: {e}")
    raise
```

### Technique 3: Element Highlighting

```python
# Highlight element before clicking (helps verify correct selection)
await page.locator(selector).evaluate("el => el.style.border = '3px solid red'")
await asyncio.sleep(1)  # Visual confirmation
await page.locator(selector).click()
```

### Technique 4: Selector Testing in Console

```python
# Evaluate JavaScript to test selectors
result = await page.evaluate("""
    (selector) => {
        const elements = document.querySelectorAll(selector);
        return {
            count: elements.length,
            visible: Array.from(elements).map(el => ({
                tag: el.tagName,
                text: el.innerText?.slice(0, 50),
                visible: el.offsetParent !== null
            }))
        };
    }
""", selector)

logger.info(f"Selector test: {result}")
```

## Fallback Selector Strategies

### Strategy 1: Selector Array with Priority

```python
async def click_with_fallbacks(page, selectors, description="element"):
    """Try multiple selectors in order until one works."""
    for i, selector in enumerate(selectors):
        try:
            await page.locator(selector).click(timeout=3000)
            logger.info(f"{description}: Used selector {i+1}: {selector}")
            return True
        except Exception as e:
            logger.debug(f"Selector {i+1} failed: {selector} - {e}")
            continue

    raise Exception(f"All selectors failed for {description}")

# Usage
await click_with_fallbacks(page, [
    "[data-testid='save-button']",  # Best
    "button:has-text('Save')",       # Good
    ".save-button",                  # Fallback
    "button.primary"                 # Last resort
], "Save button")
```

### Strategy 2: Smart Waiting

```python
async def smart_wait(page, selector, max_wait=10000):
    """Wait with multiple strategies."""
    try:
        # Try standard wait
        await page.wait_for_selector(selector, timeout=max_wait)
        return True
    except:
        # Try waiting for network idle
        await page.wait_for_load_state("networkidle")
        try:
            await page.wait_for_selector(selector, timeout=2000)
            return True
        except:
            # Last resort: just wait a bit
            await asyncio.sleep(2)
            return await page.locator(selector).count() > 0
```

### Strategy 3: Iframe Detection

```python
async def locate_in_page_or_iframe(page, selector):
    """Try locating element in main page or iframes."""
    # Try main page first
    if await page.locator(selector).count() > 0:
        return page.locator(selector)

    # Try each iframe
    for frame in page.frames():
        if frame != page.main_frame:
            if await frame.locator(selector).count() > 0:
                logger.info(f"Found in iframe: {frame.url}")
                return frame.locator(selector)

    raise Exception(f"Element not found in page or iframes: {selector}")
```

## Platform-Specific Debug Patterns

### Mailchimp

```python
# Template editor often not ready immediately
await page.goto(template_url)
await page.wait_for_load_state("networkidle")

# Wait for editor iframe specifically
await page.wait_for_function("""
    () => {
        const iframe = document.querySelector('#editingZone iframe');
        return iframe && iframe.contentDocument?.readyState === 'complete';
    }
""", timeout=15000)

iframe = await page.locator("#editingZone iframe").element_handle()
content_frame = await iframe.content_frame()
```

### Klaviyo

```python
# Klaviyo uses React, elements load in stages
await page.goto(url)
await page.wait_for_load_state("networkidle")

# Wait for React app to mount
await page.wait_for_selector("[data-reactroot], #root > div", timeout=10000)

# Additional wait for content
await asyncio.sleep(1)
```

### Yotpo

```python
# Yotpo has aggressive loading states
await page.goto(url)

# Wait for loading spinner to disappear
await page.locator(".loading-spinner").wait_for(state="hidden", timeout=15000)

# Then wait for content
await page.wait_for_selector(".campaign-list", timeout=10000)
```

## Logging Best Practices

```python
# Log selector attempts with context
logger.info(f"Attempting to click: {selector}")
logger.debug(f"Page URL: {page.url}")
logger.debug(f"Frame count: {len(page.frames())}")

try:
    await page.locator(selector).click()
    logger.info(f"✓ Successfully clicked: {selector}")
except Exception as e:
    # Log comprehensive debug info
    logger.error(f"✗ Click failed: {selector}")
    logger.error(f"Error: {e}")
    logger.error(f"Page title: {await page.title()}")
    logger.error(f"Element count: {await page.locator(selector).count()}")

    # Take screenshot
    screenshot_path = f"debug/error_{int(time.time())}.png"
    await page.screenshot(path=screenshot_path)
    logger.error(f"Screenshot saved: {screenshot_path}")

    raise
```

## Testing Selectors Before Deployment

```python
# Create selector validation function
async def validate_selectors(page, selector_map):
    """Test all selectors on current page."""
    results = {}

    for name, selector in selector_map.items():
        try:
            count = await page.locator(selector).count()
            visible = await page.locator(selector).first.is_visible() if count > 0 else False
            results[name] = {"count": count, "visible": visible, "valid": count > 0}
        except Exception as e:
            results[name] = {"error": str(e), "valid": False}

    return results

# Usage
selectors = {
    "save_button": "button:has-text('Save')",
    "template_title": "input[name='template-name']",
    "content_area": ".template-content"
}

validation = await validate_selectors(page, selectors)
for name, result in validation.items():
    if not result.get("valid"):
        logger.warning(f"Selector '{name}' is invalid: {result}")
```

## Next Steps

- See `reference/selector-cookbook.md` for tested selector patterns per platform
- Check `reference/debugging-checklist.md` for systematic debugging workflow
- Review `reference/common-fixes.md` for quick solutions to frequent issues
