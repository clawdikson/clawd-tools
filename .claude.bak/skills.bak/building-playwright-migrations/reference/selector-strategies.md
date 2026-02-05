# Selector Strategies for ESP Platforms

Robust selector patterns for email service provider platforms that frequently change their UI.

## Selector Priority Order

1. **Role-based selectors** (most stable)
2. **Data attributes** (stable if platform uses them)
3. **Class names with wildcards** (moderate stability)
4. **Text content** (language-dependent but reliable)
5. **CSS selectors** (least stable, avoid if possible)

## Mailchimp-Specific Patterns

### Template Editor (iframe-based)

```python
# Always check for iframe first
iframe_elem = await page.locator("#editingZone iframe").element_handle()
if not iframe_elem:
    iframe_elem = await page.locator("iframe[id*='editing']").element_handle()

content_frame = await iframe_elem.content_frame() if iframe_elem else None
```

### Content Blocks

```python
# Flexible selector that works across Mailchimp versions
content_blocks = await content_frame.locator(
    "td.mceSectionBody td.mceColumn > table > tbody > tr"
).all()
```

### Add Content Buttons

```python
# Use role when available
await page.get_by_role("button", name="Add", exact=True).click()

# Fallback to class pattern
await page.locator("button[class*='addContent']").click()
```

## Klaviyo-Specific Patterns

### Template Builder

```python
# Klaviyo uses data-testid attributes
await page.locator("[data-testid='add-text-block']").click()

# Fallback to button text
await page.get_by_role("button", name="Add text").click()
```

### Flow Builder

```python
# API-based approach preferred for flows
# UI selectors change frequently in flow builder
# Use backend proxy instead: klaviyo_apis/backend_klaviyo_client.py
```

## Yotpo-Specific Patterns

### Campaign List

```python
# Yotpo uses semantic HTML better
campaigns = await page.locator("div[data-campaign-id]").all()

# Text-based selection for buttons
await page.get_by_text("Create Campaign", exact=False).click()
```

## Universal Patterns

### Wait Strategies

```python
# For SPAs, wait for network idle
await page.wait_for_load_state("networkidle")

# For specific elements with retry
async def wait_for_element(page, selector, timeout=10000):
    try:
        await page.wait_for_selector(selector, timeout=timeout)
        return True
    except:
        return False
```

### Iframe Navigation

```python
async def get_editor_iframe(page):
    """Get editor iframe with multiple fallback strategies."""
    selectors = [
        "#editingZone iframe",
        "iframe[id*='edit']",
        "iframe[class*='editor']",
        "iframe[name*='template']"
    ]

    for selector in selectors:
        iframe = await page.locator(selector).element_handle()
        if iframe:
            return await iframe.content_frame()

    return None
```

### Dynamic Content

```python
# Wait for content to be loaded
await page.wait_for_function(
    "() => document.querySelectorAll('.content-block').length > 0"
)

# Or use visible check
await page.locator(".content-block").first.wait_for(state="visible")
```

## Handling Selector Changes

### Version Detection

```python
# Detect platform version to use appropriate selectors
page_content = await page.content()

if "v2-editor" in page_content:
    selector = "div.v2-content-block"
else:
    selector = "div.v1-content-block"
```

### Selector Testing

```python
async def try_selectors(page, selectors_list):
    """Try multiple selectors until one works."""
    for selector in selectors_list:
        try:
            element = await page.locator(selector).first.element_handle(timeout=2000)
            if element:
                logger.info(f"Using selector: {selector}")
                return element
        except:
            continue

    raise Exception("No working selectors found")
```

## Best Practices

1. **Always have fallback selectors** - Primary selector should be most stable, fallbacks for compatibility
2. **Log which selector worked** - Helps identify when platform UI changes
3. **Use exact=False for text matching** - More flexible for UI updates
4. **Avoid nth-child selectors** - Fragile when platform adds/removes elements
5. **Prefer data attributes** - Create your own if possible via page.evaluate()
