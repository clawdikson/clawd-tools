---
name: tracing-migration-errors
description: Trace and debug errors in ESP migrations across the full stack (Frontend→Backend→Native App→Playwright). Covers error patterns, logging strategies, debugging tools, and common failure scenarios. Use when migrations fail or behave unexpectedly.
---

# Tracing Migration Errors

Debug ESP migration failures across the entire Beena stack from user action in frontend to Playwright automation in native app. Focuses on systematic error tracing, logging patterns, and common failure scenarios.

## When to Use This Skill

- Migration job fails with unclear error message
- Frontend shows "migration failed" but no details
- Playwright automation times out or hangs
- Data not migrating correctly between platforms
- OAuth connection issues during migration
- Payment validation failures blocking migrations
- Progress tracking stops updating
- Jobs stuck in "processing" state

## Error Flow Architecture

### Full Migration Flow

```
User Action (Frontend)
  ↓ API Call
Backend API (/users/workflows/:id/run)
  ↓ HTTP Request
Native App FastAPI (/automation/run)
  ↓ Job Queue (JobStatusManager)
Playwright Worker
  ↓ Browser Automation
ESP Platform (Mailchimp/Klaviyo/etc)
  ↓ Success/Failure
Update Job Status
  ↓ Poll Status
Backend API (/automation/status/:job_id)
  ↓ Display
Frontend UI (Progress/Error Display)
```

### Error Injection Points

1. **Frontend**: Form validation, API call failures
2. **Backend**: Authentication, authorization, database errors
3. **Native App API**: Job creation, config issues
4. **Job Queue**: Queue full, worker not running
5. **Playwright Worker**: Browser crashes, timeout, selector failures
6. **ESP Platform**: Rate limits, authentication expired, data validation
7. **Status Update**: Communication failures, data corruption

## Systematic Debugging Approach

### Step 1: Identify Error Location

#### Frontend Console

```javascript
// Check browser console for errors
console.log("Migration started:", migrationId);

// Check network tab for failed requests
// Look for 4xx/5xx responses

// Check React Query dev tools
// Look at query/mutation states
```

#### Backend Logs

```bash
# Check backend logs
tail -f logs/app.log

# Search for specific job
grep "job_abc123" logs/app.log

# Filter by error level
grep "ERROR" logs/app.log | grep "migration"
```

#### Native App Logs

```bash
# macOS logs location
tail -f /tmp/beenanativeapp.log

# Windows logs
type C:\Users\Username\AppData\Local\Temp\beenanativeapp.log

# Search for job ID
grep "job_abc123" /tmp/beenanativeapp.log
```

### Step 2: Trace Error Through Stack

#### Frontend Error Tracing

```typescript
// In migration workflow hook
const { mutate: startMigration } = useMutation({
  mutationFn: (data) => runAutomation(data),
  onSuccess: (response) => {
    console.log("[Frontend] Migration started:", response.job_id);
    // Start polling
  },
  onError: (error: any) => {
    console.error("[Frontend] Migration failed to start:", {
      status: error?.response?.status,
      message: error?.response?.data?.message,
      details: error?.response?.data?.detail,
    });

    // Check specific error types
    if (error?.response?.status === 401) {
      console.error("[Frontend] Authentication error - token expired?");
    } else if (error?.response?.status === 403) {
      console.error("[Frontend] Authorization error - missing permissions?");
    } else if (error?.response?.status === 402) {
      console.error("[Frontend] Payment required - user not subscribed?");
    }
  },
});
```

#### Backend Error Tracing

```javascript
// In Express route
router.post("/automation/run", async (req, res) => {
  const jobId = `job_${Date.now()}`;
  logger.info(`[Backend ${jobId}] Received migration request`, {
    userId: req.user._id,
    source: req.body.source,
    destination: req.body.destination,
  });

  try {
    // Call native app API
    const response = await axios.post(
      `${NATIVE_APP_URL}/automation/run`,
      req.body,
      { timeout: 30000 },
    );

    logger.info(`[Backend ${jobId}] Native app accepted job`, {
      nativeJobId: response.data.job_id,
    });

    res.json({ success: true, job_id: response.data.job_id });
  } catch (error) {
    logger.error(`[Backend ${jobId}] Failed to submit to native app`, {
      error: error.message,
      code: error.code,
      response: error.response?.data,
    });

    if (error.code === "ECONNREFUSED") {
      logger.error(`[Backend ${jobId}] Native app not running`);
      res.status(503).json({
        error: "Native app is not running. Please start the Beena app.",
      });
    } else {
      res.status(500).json({
        error: "Failed to start migration",
        details: error.message,
      });
    }
  }
});
```

#### Native App Error Tracing

```python
# In FastAPI endpoint
@router.post("/automation/run")
async def run_automation(
    request: AutomationRequest,
    job_manager: JobStatusManager = Depends(get_job_status_manager)
):
    logger.info(f"[Native App] Received automation request", extra={
        "actions_count": len(request.actions),
        "has_selected_items": hasattr(request, 'selectedItems'),
    })

    try:
        # Create and queue job
        job_id = job_manager.create_job(actions=request.actions)

        logger.info(f"[Native App {job_id}] Job created and queued", extra={
            "queue_size": job_manager.job_queue.qsize(),
        })

        return {
            "success": True,
            "job_id": job_id,
            "message": "Job queued successfully"
        }

    except queue.Full:
        logger.error("[Native App] Job queue is full")
        raise HTTPException(
            status_code=503,
            detail="Job queue is full. Please wait for current jobs to complete."
        )
    except Exception as e:
        logger.error(f"[Native App] Failed to create job: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue job: {str(e)}"
        )
```

#### Worker Error Tracing

```python
# In Playwright worker
async def process_job(job: Job):
    job_id = job.job_id
    logger.info(f"[Worker {job_id}] Starting job processing", extra={
        "actions_count": len(job.actions),
    })

    try:
        # Process each action
        for idx, action in enumerate(job.actions):
            logger.info(f"[Worker {job_id}] Processing action {idx+1}/{len(job.actions)}", extra={
                "function": action.get("function"),
            })

            result = await execute_action(action)

            logger.info(f"[Worker {job_id}] Action {idx+1} completed", extra={
                "result_status": result.get("status"),
            })

        # Success
        job_manager.update_job_status(
            job_id,
            JobState.SUCCESS,
            result={"message": "All actions completed"}
        )

        logger.info(f"[Worker {job_id}] Job completed successfully")

    except PlaywrightTimeoutError as e:
        logger.error(f"[Worker {job_id}] Timeout error: {e}", exc_info=True, extra={
            "selector": getattr(e, 'selector', None),
            "timeout": getattr(e, 'timeout', None),
        })

        job_manager.update_job_status(
            job_id,
            JobState.FAILED,
            error_message=f"Timeout waiting for element: {e}"
        )

    except PlaywrightError as e:
        logger.error(f"[Worker {job_id}] Playwright error: {e}", exc_info=True)

        job_manager.update_job_status(
            job_id,
            JobState.FAILED,
            error_message=f"Browser automation failed: {e}"
        )

    except Exception as e:
        logger.error(f"[Worker {job_id}] Unexpected error: {e}", exc_info=True)

        job_manager.update_job_status(
            job_id,
            JobState.FAILED,
            error_message=f"Unexpected error: {e}"
        )
```

## Common Error Scenarios

### 1. OAuth Connection Expired

**Symptoms:**

- Migration fails with "Authentication failed"
- Klaviyo API returns 401 Unauthorized

**Diagnosis:**

```python
# Check token expiration
logger.info(f"OAuth token expires at: {token_expires_at}")
if datetime.now(timezone.utc) > token_expires_at:
    logger.error("OAuth token expired")
```

**Solution:**

```python
# Refresh token before migration
if is_token_expired(token):
    logger.info("Refreshing expired OAuth token")
    new_token = await refresh_oauth_token(refresh_token)
    # Update in database
```

### 2. Selector Not Found (Timeout)

**Symptoms:**

- Playwright times out waiting for element
- Error: "Timeout 60000ms exceeded"

**Diagnosis:**

```python
# Add debug screenshot before timeout
try:
    await page.wait_for_selector(selector, timeout=60000)
except TimeoutError:
    # Take screenshot for debugging
    await page.screenshot(path=f"debug_{job_id}_timeout.png")
    logger.error(f"Selector not found: {selector}", extra={
        "current_url": page.url,
        "page_title": await page.title(),
    })
    raise
```

**Solution:**

```python
# Use fallback selectors
selectors = [
    "[data-testid='save-button']",
    "button:has-text('Save')",
    ".save-button",
    "//button[contains(., 'Save')]"
]

for selector in selectors:
    try:
        await page.wait_for_selector(selector, timeout=5000)
        logger.info(f"Found element with selector: {selector}")
        break
    except TimeoutError:
        logger.warn(f"Selector failed: {selector}")
        continue
else:
    # All selectors failed
    raise SelectorNotFoundError("Save button not found with any selector")
```

### 3. Rate Limiting

**Symptoms:**

- API returns 429 Too Many Requests
- Migration slows down or fails mid-way

**Diagnosis:**

```python
# Check rate limit headers
response_headers = response.headers
logger.info("Rate limit status", extra={
    "rate_limit": response_headers.get("X-RateLimit-Limit"),
    "rate_remaining": response_headers.get("X-RateLimit-Remaining"),
    "rate_reset": response_headers.get("X-RateLimit-Reset"),
})
```

**Solution:**

```python
# Implement exponential backoff
async def api_call_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = await make_request(url)
            return response
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential: 1s, 2s, 4s
                logger.warn(f"Rate limited, waiting {wait_time}s before retry")
                await asyncio.sleep(wait_time)
            else:
                logger.error("Rate limit retries exhausted")
                raise
```

### 4. Payment Validation Failure

**Symptoms:**

- Migration blocked with "Payment required"
- Frontend shows 402 status

**Diagnosis:**

```python
# Check payment status
logger.info(f"[Payment] Validating for user {user_id}")
payment_status = await validate_payment(user_id)
logger.info(f"[Payment] Status: {payment_status}", extra={
    "is_paid": payment_status.get("is_paid"),
    "subscription_expires": payment_status.get("expires_at"),
})
```

**Solution:**

```python
# Cache payment validation
PAYMENT_CACHE = {}

async def validate_payment_cached(user_id):
    cache_key = f"payment_{user_id}"

    # Check cache first
    if cache_key in PAYMENT_CACHE:
        cached = PAYMENT_CACHE[cache_key]
        if cached["expires_at"] > datetime.now():
            logger.info(f"[Payment] Using cached validation for {user_id}")
            return cached["status"]

    # Fetch from backend
    status = await fetch_payment_status(user_id)

    # Cache for 30 minutes
    PAYMENT_CACHE[cache_key] = {
        "status": status,
        "expires_at": datetime.now() + timedelta(minutes=30)
    }

    return status
```

### 5. Progress Not Updating

**Symptoms:**

- Frontend progress bar stuck
- Job shows "processing" but no updates

**Diagnosis:**

```python
# Check job status manager
job = job_manager.get_job(job_id)
logger.info(f"[Debug {job_id}] Job state", extra={
    "status": job.status.value,
    "progress_details": job.progress_details,
    "last_updated": job.updated_at,
})
```

**Solution:**

```python
# Update progress frequently
async def migrate_items(items, job_id):
    total = len(items)

    for idx, item in enumerate(items):
        # Process item
        await process_item(item)

        # Update progress every item
        job_manager.update_job_progress(
            job_id,
            {
                "total_items": total,
                "completed_items": idx + 1,
                "current_item": item["name"],
                "percentage": ((idx + 1) / total) * 100
            }
        )

        # Log progress periodically
        if (idx + 1) % 10 == 0:
            logger.info(f"[Worker {job_id}] Progress: {idx+1}/{total}")
```

## Debugging Tools

### 1. Playwright Inspector

```python
# Enable Playwright inspector
import os
os.environ["PWDEBUG"] = "1"

# Slow down operations for visibility
page.set_default_timeout(0)  # Disable timeout
page.set_default_navigation_timeout(0)

# Pause execution for inspection
await page.pause()
```

### 2. Screenshots and Videos

```python
# Take screenshot on error
try:
    await page.click(selector)
except Exception as e:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = f"debug_{job_id}_{timestamp}.png"
    await page.screenshot(path=screenshot_path)
    logger.error(f"Error screenshot saved to {screenshot_path}")
    raise

# Record video of entire session
browser = await playwright.chromium.launch(
    headless=False,
    args=["--start-maximized"]
)
context = await browser.new_context(
    record_video_dir=f"videos/{job_id}/"
)
```

### 3. Network Logging

```python
# Log all network requests
async def log_request(request):
    logger.debug(f"[Network] Request: {request.method} {request.url}")

async def log_response(response):
    logger.debug(f"[Network] Response: {response.status} {response.url}")

page.on("request", log_request)
page.on("response", log_response)

# Log failed requests
async def log_failed_request(request):
    logger.error(f"[Network] Failed: {request.url}", extra={
        "method": request.method,
        "failure": request.failure,
    })

page.on("requestfailed", log_failed_request)
```

### 4. Console Logging

```python
# Capture browser console logs
async def handle_console_message(msg):
    logger.info(f"[Browser Console] {msg.type}: {msg.text}")

page.on("console", handle_console_message)

# Capture page errors
async def handle_page_error(error):
    logger.error(f"[Browser Error] {error}")

page.on("pageerror", handle_page_error)
```

## Error Reporting Patterns

### Structured Logging

```python
# Use structured logging with context
logger.error("Migration failed", extra={
    "job_id": job_id,
    "user_id": user_id,
    "source": "mailchimp",
    "destination": "klaviyo",
    "action": "migrate_contacts",
    "error_type": type(e).__name__,
    "error_message": str(e),
    "stack_trace": traceback.format_exc(),
})
```

### Error Context Preservation

```python
# Preserve context through error chain
class MigrationError(Exception):
    def __init__(self, message, job_id=None, action=None, original_error=None):
        self.message = message
        self.job_id = job_id
        self.action = action
        self.original_error = original_error
        super().__init__(message)

    def to_dict(self):
        return {
            "message": self.message,
            "job_id": self.job_id,
            "action": self.action,
            "original_error": str(self.original_error) if self.original_error else None,
        }

# Use in error handling
try:
    await migrate_contacts()
except Exception as e:
    raise MigrationError(
        "Failed to migrate contacts",
        job_id=job_id,
        action="migrate_contacts",
        original_error=e
    )
```

### User-Friendly Error Messages

```python
# Map technical errors to user-friendly messages
ERROR_MESSAGES = {
    "TimeoutError": "The migration took too long. This might be due to slow internet or the platform being slow to respond.",
    "AuthenticationError": "Your connection to {platform} has expired. Please reconnect your account.",
    "RateLimitError": "We're being rate-limited by {platform}. The migration will retry automatically.",
    "SelectorNotFoundError": "We couldn't find a required element on the page. The {platform} interface may have changed.",
}

def get_user_friendly_error(error_type, platform):
    template = ERROR_MESSAGES.get(error_type, "An unexpected error occurred during migration.")
    return template.format(platform=platform)
```

## Best Practices

1. **Log at every stage** - Request received, job queued, processing started, completed
2. **Include context** - Job ID, user ID, action name in all logs
3. **Use structured logging** - JSON format for easy parsing
4. **Preserve error chain** - Wrap errors, don't swallow them
5. **Take screenshots** on failures for visual debugging
6. **Set appropriate timeouts** - Don't wait forever, fail fast
7. **Implement retry logic** - With exponential backoff
8. **Monitor queue health** - Alert if queue fills up
9. **Track job lifecycle** - From creation to completion
10. **Test error paths** - Simulate failures to verify error handling

## Debugging Checklist

When migration fails:

- [ ] Check frontend console for errors
- [ ] Check backend logs for the job ID
- [ ] Check native app logs for the job ID
- [ ] Verify OAuth tokens are valid
- [ ] Check payment validation status
- [ ] Look for rate limiting errors
- [ ] Take screenshot at point of failure
- [ ] Review Playwright selector
- [ ] Check network requests in browser DevTools
- [ ] Verify ESP platform is accessible
- [ ] Check job queue status (not full?)
- [ ] Verify worker thread is running
- [ ] Review job progress updates
- [ ] Check for timeout errors
- [ ] Look for JavaScript errors in browser console

## Next Steps

- See `building-playwright-migrations` for migration function patterns
- Check `managing-migration-workflows` for frontend error handling
- Review `extending-fastapi-server` for API error handling
- See `reference/error-codes.md` for complete error code reference
