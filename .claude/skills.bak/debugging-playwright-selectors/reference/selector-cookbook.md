# Selector Cookbook - Tested Patterns

Proven selectors for common elements across ESP platforms.

## Mailchimp Selectors

### Template Editor

```python
# Editor iframe
editor_iframe = "#editingZone iframe"
editor_iframe_fallback = "iframe[id*='editing'], iframe[src*='template']"

# Content blocks in iframe (use content_frame)
content_blocks = "td.mceSectionBody td.mceColumn > table > tbody > tr"
content_column = "td.mceColumn"

# Add content button (main page)
add_button = "button:has-text('Add')"
add_button_exact = 'button[name="Add"]'

# Template title
template_title = "div[class*='titleMenuContainer']"
template_name_input = "input[type='text'][placeholder*='name']"

# Save button
save_button = "button:has-text('Save')"
```

### Campaign List

```python
# Campaign rows
campaign_items = "table tr[data-campaign-id]"
campaign_titles = "td.campaign-name"

# Create campaign button
create_button = "button:has-text('Create Campaign')"

# Campaign status
status_badge = ".campaign-status"
```

## Klaviyo Selectors

### Template Builder

```python
# Add blocks (no iframe, main page)
add_text_block = "[data-testid='add-text-block']"
add_image_block = "[data-testid='add-image-block']"
add_button_block = "[data-testid='add-button-block']"

# Fallback to button text
add_text_fallback = "button:has-text('Add text')"
add_image_fallback = "button:has-text('Add image')"

# Template name
template_name = "input[placeholder='Template name']"
template_name_alt = "input[name='template-name']"

# Content editor
content_editable = "[contenteditable='true']"
text_editor = ".ql-editor"  # Quill editor

# Save
save_button = "button:has-text('Save template')"
save_button_icon = "button svg[data-icon='save']"
```

### Flow Builder

```python
# Flow actions (complex, prefer API)
add_action_button = "button:has-text('Add action')"
send_email_action = "[data-action-type='send-email']"

# Trigger selection
trigger_dropdown = "[data-testid='trigger-select']"
trigger_options = "[role='option']"
```

### Asset Library

```python
# Image upload
upload_button = "button:has-text('Upload images')"
import_url_tab = "button[role='tab']:has-text('Import URL')"
image_url_input = "input[placeholder*='URL'], input[name='image-url']"
import_image_button = "button:has-text('Import image')"

# Image grid
uploaded_images = ".asset-grid img"
image_item = ".asset-item"
```

## Yotpo Selectors

### Campaign Editor

```python
# Editor iframe for preview
editor_preview = "iframe.campaign-preview"

# Campaign form fields
campaign_name = "input[name='campaign_name']"
subject_line = "input[name='subject']"
preview_text = "input[name='preview_text']"

# Audience selection
select_list = "select[name='list_id']"
list_options = "select[name='list_id'] option"

# Template selection
template_selector = ".template-grid .template-item"
select_template_button = "button:has-text('Use this template')"
```

### Flow Builder

```python
# Flow types
flow_type_cards = ".flow-type-card"
select_flow_type = "button[data-flow-type]"

# Flow editor
add_step_button = "button:has-text('Add step')"
step_config = ".step-configuration"
```

## Universal Patterns

### Buttons

```python
# Primary actions
primary_button = "button.primary, button[variant='primary']"
submit_button = "button[type='submit']"
save_buttons = [
    "button:has-text('Save')",
    "button[aria-label='Save']",
    "button.save-button",
    "[data-action='save']"
]

# Cancel/Close
cancel_button = "button:has-text('Cancel')"
close_modal = "button[aria-label='Close'], .modal-close"
```

### Forms

```python
# Text inputs
text_input = "input[type='text']"
named_input = lambda name: f"input[name='{name}']"
placeholder_input = lambda text: f"input[placeholder*='{text}']"

# Dropdowns
select = "select"
custom_dropdown = "[role='combobox'], [role='listbox']"
dropdown_option = "[role='option']"

# Checkboxes
checkbox = "input[type='checkbox']"
checkbox_label = "label:has(input[type='checkbox'])"
```

### Loading States

```python
# Spinners
spinner = ".loading, .spinner, [data-loading='true']"
spinner_hidden = ".loading[style*='display: none']"

# Skeleton loaders
skeleton = ".skeleton, .skeleton-loader"

# Progress bars
progress = ".progress-bar, [role='progressbar']"
```

### Modals/Dialogs

```python
# Modal container
modal = "[role='dialog'], .modal, .dialog"
modal_backdrop = ".modal-backdrop, .overlay"

# Modal buttons
modal_confirm = "dialog button:has-text('Confirm'), .modal button.primary"
modal_cancel = "dialog button:has-text('Cancel'), .modal button.secondary"
```

## Testing Selectors

```python
# Quick test script
async def test_selector(page, selector, description=""):
    """Test if selector works on current page."""
    try:
        count = await page.locator(selector).count()
        visible_count = 0

        if count > 0:
            for i in range(count):
                if await page.locator(selector).nth(i).is_visible():
                    visible_count += 1

        result = f"✓ {description or selector}: {count} total, {visible_count} visible"
        logger.info(result)
        return count > 0
    except Exception as e:
        logger.error(f"✗ {description or selector}: {e}")
        return False

# Usage
await test_selector(page, "button:has-text('Save')", "Save button")
```

## Selector Priority Ranking

**Most Stable** (use first):

1. `get_by_role()` - Accessibility roles
2. `get_by_label()` - Form labels
3. `get_by_text()` - Unique text content
4. `[data-testid]` - If platform uses test IDs

**Moderate Stability**: 5. `[aria-*]` attributes 6. Semantic HTML tags (`button`, `nav`, `article`) 7. Class names with wildcards (`[class*='save']`)

**Least Stable** (fallback only): 8. Specific class names 9. ID selectors (if IDs are dynamic) 10. Complex CSS selectors 11. nth-child/nth-of-type

## Platform Version Detection

```python
async def detect_platform_version(page):
    """Detect platform version to use appropriate selectors."""
    content = await page.content()

    versions = {
        "mailchimp_v2": "v2-editor" in content,
        "klaviyo_new_ui": "data-reactroot" in content,
        "yotpo_legacy": "yotpo-legacy" in content
    }

    logger.info(f"Platform versions detected: {versions}")
    return versions
```
