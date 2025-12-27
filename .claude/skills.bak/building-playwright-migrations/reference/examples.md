# Complete Migration Examples

Real-world migration implementations from the Beena codebase.

## Example 1: Simple Contact Export

Minimal migration function that exports contacts from Mailchimp:

```python
async def export_mailchimp_contacts(
    page: Page,
    params: Dict[str, Any],
    logger
) -> Dict[str, Any]:
    """
    Export contacts from Mailchimp audience.

    Args:
        page: Playwright page (already at Mailchimp audience page)
        params: {"audience_id": "abc123"}
        logger: Logger instance

    Returns:
        {"status": "success", "data": {"contacts": [...], "count": 1000}}
    """
    try:
        audience_id = params.get("audience_id")
        if not audience_id:
            return {"status": "failed", "error": "audience_id required"}

        # Navigate to contacts
        await page.goto(f"https://admin.mailchimp.com/lists/members/?id={audience_id}")
        await page.wait_for_load_state("networkidle")

        # Click export button
        await page.get_by_role("button", name="Export Audience").click()
        await page.get_by_text("Export as CSV").click()

        # Wait for download
        async with page.expect_download() as download_info:
            await page.get_by_role("button", name="Export").click()

        download = await download_info.value
        file_path = await download.path()

        # Parse CSV
        import csv
        contacts = []
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            contacts = list(reader)

        logger.info(f"Exported {len(contacts)} contacts")

        return {
            "status": "success",
            "data": {
                "contacts": contacts,
                "count": len(contacts)
            }
        }

    except Exception as e:
        logger.error(f"Contact export failed: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}
```

## Example 2: Template Migration with Images

Full template migration including image upload:

```python
async def migrate_mailchimp_template_to_klaviyo(
    page: Page,
    params: Dict[str, Any],
    logger
) -> Dict[str, Any]:
    """
    Migrate email template from Mailchimp to Klaviyo.

    Args:
        page: Playwright page
        params: {
            "template_id": "123",
            "template_name": "Welcome Email"
        }
        logger: Logger instance

    Returns:
        {"status": "success", "data": {"klaviyo_template_id": "xyz"}}
    """
    template_id = params.get("template_id")
    template_name = params.get("template_name", "Migrated Template")

    try:
        # Step 1: Extract from Mailchimp
        logger.info(f"Extracting template {template_id} from Mailchimp")

        await page.goto(f"https://admin.mailchimp.com/templates/edit?id={template_id}")
        await page.wait_for_load_state("networkidle")

        # Get iframe
        iframe_elem = await page.locator("#editingZone iframe").element_handle()
        content_frame = await iframe_elem.content_frame()

        # Extract content blocks
        mapped_contents = []
        content_elements = await content_frame.locator(
            "td.mceSectionBody td.mceColumn > table > tbody > tr"
        ).all()

        for elem in content_elements:
            # Detect block type
            block_type = await detect_block_type(elem)

            if block_type == "image":
                img = await elem.locator("img").first.element_handle()
                mapped_contents.append({
                    "type": "image",
                    "url": await img.get_attribute("src"),
                    "alt": await img.get_attribute("alt")
                })
            elif block_type == "text":
                text = await elem.locator("td").first.text_content()
                mapped_contents.append({
                    "type": "text",
                    "content": text
                })

        # Extract styles
        body_styles = await extract_body_styles(content_frame)

        # Step 2: Extract and upload images to Klaviyo
        logger.info("Uploading images to Klaviyo")

        images = [item for item in mapped_contents if item["type"] == "image"]
        klaviyo_page = await page.context.new_page()
        await klaviyo_page.goto("https://www.klaviyo.com/asset-library/images")

        for image in images:
            await klaviyo_page.get_by_role("button", name="Upload images").click()
            await klaviyo_page.get_by_role("tab", name="Import URL").click()
            await klaviyo_page.get_by_role("textbox", name="Image URL").fill(image["url"])
            await klaviyo_page.get_by_role("button", name="Import image").click()
            await asyncio.sleep(1)

        await klaviyo_page.close()

        # Step 3: Build template in Klaviyo
        logger.info("Building template in Klaviyo")

        await page.goto("https://www.klaviyo.com/email-templates/create")
        await page.get_by_role("button", name="Start from scratch").click()

        # Set template name
        await page.get_by_role("textbox", name="Template name").fill(template_name)

        # Add content blocks
        for item in reversed(mapped_contents):  # Klaviyo builds bottom-up
            if item["type"] == "text":
                await page.get_by_role("button", name="Add text block").click()
                await page.locator("[contenteditable='true']").last.fill(item["content"])
            elif item["type"] == "image":
                await page.get_by_role("button", name="Add image block").click()
                await page.get_by_role("button", name="Select from library").click()
                # Find and select the uploaded image
                await page.locator(f"img[src*='{image['url'].split('/')[-1]}']").click()
                await page.get_by_role("button", name="Insert").click()

        # Save template
        await page.get_by_role("button", name="Save").click()
        await page.wait_for_url("**/email-templates/**")

        # Get new template ID from URL
        klaviyo_template_id = page.url.split("/")[-1]

        logger.info(f"Template migrated successfully: {klaviyo_template_id}")

        return {
            "status": "success",
            "data": {
                "klaviyo_template_id": klaviyo_template_id,
                "blocks_migrated": len(mapped_contents)
            }
        }

    except Exception as e:
        logger.error(f"Template migration failed: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}
```

## Example 3: Flow Migration via API

Complex flow migration using backend API proxy:

```python
async def migrate_mailchimp_automation_to_klaviyo(
    page: Page,
    params: Dict[str, Any],
    logger
) -> Dict[str, Any]:
    """
    Migrate automation flow from Mailchimp to Klaviyo using API.

    Args:
        page: Playwright page (for auth context)
        params: {"automation_id": "abc123"}
        logger: Logger instance

    Returns:
        {"status": "success", "data": {"flow_id": "flow_xyz"}}
    """
    from beenanativeapp.services.universal_mapping.flow_converters import (
        convert_mailchimp_to_universal,
        convert_universal_to_klaviyo
    )
    from beenanativeapp.services.playwright.custom_functions.mailchimp_to_klaviyo_components.automation_flow.klaviyo_apis.backend_klaviyo_client import BackendKlaviyoClient

    automation_id = params.get("automation_id")

    try:
        # Step 1: Extract flow from Mailchimp
        logger.info(f"Extracting automation {automation_id}")

        await page.goto(f"https://admin.mailchimp.com/automations/edit/{automation_id}")
        await page.wait_for_load_state("networkidle")

        # Intercept API response instead of parsing UI
        flow_data = None

        async def handle_response(response):
            nonlocal flow_data
            if "/automations/" in response.url:
                flow_data = await response.json()

        page.on("response", handle_response)

        # Trigger API call by navigating
        await page.reload()
        await asyncio.sleep(2)

        if not flow_data:
            raise Exception("Failed to intercept flow data")

        # Step 2: Convert to universal format
        logger.info("Converting to universal schema")
        universal_flow = convert_mailchimp_to_universal(flow_data)

        # Step 3: Convert to Klaviyo format
        klaviyo_flow = convert_universal_to_klaviyo(universal_flow)

        # Step 4: Create flow via API
        logger.info("Creating flow in Klaviyo via API")

        klaviyo_client = BackendKlaviyoClient(logger)

        # Create flow
        flow_response = await klaviyo_client.create_flow({
            "name": klaviyo_flow["name"],
            "status": "draft",
            "trigger_type": klaviyo_flow["trigger"]["type"]
        })

        flow_id = flow_response["data"]["id"]

        # Add flow actions
        for action in klaviyo_flow["actions"]:
            await klaviyo_client.add_flow_action(flow_id, action)

        logger.info(f"Flow created: {flow_id}")

        return {
            "status": "success",
            "data": {
                "flow_id": flow_id,
                "actions_count": len(klaviyo_flow["actions"])
            }
        }

    except Exception as e:
        logger.error(f"Flow migration failed: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}
```

## Helper Functions

### Block Type Detection

```python
async def detect_block_type(element):
    """Detect Mailchimp content block type."""
    classes = await element.get_attribute("class") or ""

    if "mceText" in classes:
        return "text"
    elif "mceImage" in classes:
        return "image"
    elif "mceButton" in classes:
        return "button"
    elif "mceDivider" in classes:
        return "divider"

    # Fallback: check for child elements
    has_img = await element.locator("img").count() > 0
    if has_img:
        return "image"

    return "text"  # Default
```

### Style Extraction

```python
async def extract_body_styles(content_frame):
    """Extract body section styles from template."""
    body_section = await content_frame.locator("td.mceSectionBody").first

    styles = {}

    if body_section:
        # Get inline styles
        style_attr = await body_section.get_attribute("style") or ""

        # Parse style attribute
        for style_rule in style_attr.split(";"):
            if ":" in style_rule:
                prop, value = style_rule.split(":", 1)
                styles[prop.strip()] = value.strip()

    return styles
```
