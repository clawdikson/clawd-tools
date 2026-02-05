---
name: building-playwright-migrations
description: Creates custom migration functions for ESP platforms (Mailchimp, Klaviyo, Yotpo) following Beena's standard interface. Handles DOM extraction, template building, and automation flow mapping. Use when adding new platform integrations or extending existing ESP migrations.
---

# Building Playwright Migrations

Develop custom migration functions for email service provider (ESP) platforms in the Beena Native App. This skill covers the project-specific patterns, standard interface, and best practices for creating reliable migration workflows.

## When to Use This Skill

- Adding new ESP platform integrations (e.g., ActiveCampaign → Klaviyo)
- Extending existing migrations with new features (templates, flows, contacts)
- Debugging migration failures related to extraction or transformation
- Refactoring migration code for better reliability

## Standard Migration Function Interface

All custom functions in `services/playwright/custom_functions/` must follow this signature:

```python
async def function_name(page: Page, params: Dict[str, Any], logger) -> Dict[str, Any]:
    """
    Migration function description.

    Args:
        page: Playwright Page instance (already navigated to source platform)
        params: Dictionary containing migration parameters from API request
        logger: Configured logger instance for structured logging

    Returns:
        Dict with 'status' and 'data' keys
    """
    try:
        # Implementation
        return {"status": "success", "data": result_data}
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}
```

## Migration Workflow Pattern

### 1. **Extract from Source Platform**

Extract data using iframe navigation, DOM parsing, and network interception:

```python
# Navigate to iframe if needed (common in ESP platforms)
iframe_element = await page.locator("#editingZone iframe").element_handle()
content_frame = await iframe_element.content_frame() if iframe_element else None

# Extract elements from iframe
if content_frame:
    elements = await content_frame.locator("td.mceSectionBody td.mceColumn").all()
```

**Key patterns**:

- ESP platforms often use iframes for editors - check `workflow.py` for examples
- Use network interception to capture API responses (saves DOM parsing)
- Always add error handling for missing iframes/elements

### 2. **Transform to Universal Format**

Map platform-specific data to intermediate format before building in destination:

```python
mapped_contents = []

for element in source_elements:
    processed = {
        "type": detect_element_type(element),  # "text", "image", "button", etc.
        "content": extract_content(element),
        "styles": extract_styles(element)
    }
    mapped_contents.append(processed)
```

**Universal schema location**: `services/universal_mapping/universal_flow_schema.py`

### 3. **Build in Destination Platform**

Construct templates/flows in destination platform using their UI or API:

```python
# For UI-based building (e.g., Klaviyo templates)
for content_item in mapped_contents:
    if content_item["type"] == "text":
        await add_text_block(page, content_item)
    elif content_item["type"] == "image":
        await add_image_block(page, content_item)

# For API-based building (use backend proxy)
klaviyo_api = KlaviyoApiClient(page)
flow_response = await klaviyo_api.create_flow(flow_data)
```

**Critical**: Use backend API proxy for OAuth-protected endpoints (see `klaviyo_apis/backend_klaviyo_client.py`)

## Common Migration Components

### Template Migration

Extract email templates with styles and content:

```python
# Extract body styles (background, padding, etc.)
body_section_styles = await get_body_section_styles(page, content_frame)

# Process content blocks
for content_elem in content_elements:
    processed = await _process_content_element(page, content_elem, template_data)
    if processed:
        mapped_contents.append(processed)

# Build in destination
template_id = await _build_klaviyo_template(page, {
    "title": template_name,
    "contents": mapped_contents,
    "styles": body_section_styles
})
```

**Reference**: `mailchimp_to_klaviyo_components/workflow.py`

### Campaign Migration

Migrate sent/draft campaigns with audiences and settings:

```python
# Extract campaign data
campaign_data = await extract_campaign_from_source(page, campaign_id)

# Upload assets (images) to destination
images = _extract_images_from_campaign(campaign_data["template"])
await _add_images_to_klaviyo(page, images)

# Create campaign
await _create_klaviyo_actual_campaign_page(page, campaign_data["name"])
await _select_subject_in_klaviyo(page, campaign_data["subject"])
await _select_audience_in_klaviyo(page, campaign_data["list_id"])
```

**Reference**: `yotpo/campaign_migration.py`

### Flow/Automation Migration

Migrate automation workflows with triggers and actions:

```python
# Extract flow structure
flows = await extract_flows_from_source(page, params)

# Convert to universal format
universal_flows = convert_to_universal_schema(flows)

# Build via API (flows are too complex for UI automation)
for flow in universal_flows:
    flow_id = await klaviyo_client.create_flow(flow)
    await klaviyo_client.add_actions(flow_id, flow["actions"])
```

**Reference**: `automation_flow/m2k_automation.py`

## Error Handling Patterns

### Selector Failures

```python
try:
    await page.locator(selector).click(timeout=5000)
except Exception as e:
    logger.warning(f"Primary selector failed: {e}")
    # Try fallback selector
    await page.locator(fallback_selector).click()
```

### Missing Elements

```python
# Use conditional extraction
logo_element = await page.locator("img.logo").element_handle()
if logo_element:
    logo_url = await logo_element.get_attribute("src")
    mapped_contents.append({"type": "logo", "url": logo_url})
else:
    logger.info("No logo found, skipping")
```

### Async Timeouts

```python
# Add explicit waits for dynamic content
await page.wait_for_load_state("networkidle", timeout=10000)
await asyncio.sleep(2)  # Additional buffer for SPA rendering
```

## Project-Specific Utilities

### WorkflowErrorHandler

Use for consistent error handling across migrations:

```python
from beenanativeapp.utils.error_handler import WorkflowErrorHandler

error_handler = WorkflowErrorHandler(logger)

try:
    result = await migration_step()
except Exception as e:
    error_handler.handle_error(e, context="Template extraction")
    raise
```

### Platform Classes

Use platform abstraction for navigation and auth:

```python
from beenanativeapp.plugins.automation.platforms.esp.yotpo.platform import YotpoPlatform

yotpo = YotpoPlatform(page, logger)
await yotpo.navigate_to_campaigns()
```

**Location**: `plugins/automation/platforms/esp/{platform}/`

## Testing Migration Functions

Create unit tests in `tests/` directory:

```python
import unittest
from unittest.mock import AsyncMock, MagicMock

class TestCampaignMigration(unittest.IsolatedAsyncioTestCase):
    async def test_extract_images(self):
        # Mock campaign data
        campaign = [{"type": "image", "url": "https://example.com/img.jpg"}]

        # Test extraction
        images = _extract_images_from_campaign(campaign)

        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["url"], "https://example.com/img.jpg")
```

## Performance Considerations

- **Browser contexts**: Reuse page context for multiple operations
- **Network interception**: Capture API responses instead of heavy DOM parsing
- **Parallel operations**: Use `asyncio.gather()` for independent tasks
- **Memory**: Close pages after use (`await page.close()`)

## Common Pitfalls

1. **Forgetting async/await**: All Playwright operations are async
2. **Not handling iframes**: ESP editors usually run in iframes
3. **Hardcoded selectors**: Platform UIs change - use flexible selectors
4. **Missing error context**: Always log with context for debugging
5. **No retry logic**: Network operations should retry on transient failures

## Next Steps

- Review existing migration functions in `custom_functions/`
- Check `reference/selector-strategies.md` for robust selector patterns
- See `reference/examples.md` for complete migration implementations
- Read `reference/troubleshooting.md` for debugging failed migrations
