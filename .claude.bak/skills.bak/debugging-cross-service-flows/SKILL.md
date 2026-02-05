---
name: debugging-cross-service-flows
description: Debug issues spanning Frontend, Backend, and Native App services. Covers log correlation, service health checks, common failure patterns, and tracing requests across the system. Use when errors cross service boundaries, involve OAuth/payment validation, or require understanding multi-service workflows.
---

# Debugging Cross-Service Flows

Debug complex issues that span the Beena Automation Platform's three services. This skill covers request tracing, log correlation, common failure patterns, and systematic debugging approaches.

## When to Use This Skill

- Errors occur in one service but originate from another
- OAuth flows fail somewhere in the Frontend → Backend → Provider chain
- Payment validation fails between Native App and Backend
- Migration jobs fail with unclear error sources
- Need to trace a request across all three services

## Service Architecture Quick Reference

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                                │
│  React + TypeScript | Port 5173 | Vite Dev Server              │
│  Console: Browser DevTools | Network: DevTools Network tab      │
├─────────────────────────────────────────────────────────────────┤
                              │
                              ▼ HTTP REST
┌─────────────────────────────────────────────────────────────────┐
│                          Backend                                │
│  Node.js + Express | Port 5001 | Winston Logger                 │
│  Logs: stdout + logs/combined.log | DB: MongoDB                 │
├─────────────────────────────────────────────────────────────────┤
                              │
                              ▼ HTTP REST (validation)
┌─────────────────────────────────────────────────────────────────┐
│                        Native App                               │
│  Python + FastAPI | Port 8000 | Python logging                  │
│  Logs: beenanativeapp/logs/ | Automation: Playwright            │
└─────────────────────────────────────────────────────────────────┘
```

## Step 1: Identify the Failure Point

### Quick Health Check Script

```bash
#!/bin/bash
# health_check.sh - Run from monorepo root

echo "=== Service Health Check ==="

# Frontend
echo -n "Frontend (5173): "
curl -s http://localhost:5173 > /dev/null && echo "✓ Running" || echo "✗ Down"

# Backend
echo -n "Backend (5001): "
curl -s http://localhost:5001/api/v1/health > /dev/null && echo "✓ Running" || echo "✗ Down"

# Native App
echo -n "Native App (8000): "
curl -s http://localhost:8000/health > /dev/null && echo "✓ Running" || echo "✗ Down"

# MongoDB
echo -n "MongoDB (27017): "
mongosh --eval "db.runCommand({ping:1})" --quiet 2> /dev/null && echo "✓ Running" || echo "✗ Down"

echo ""
echo "=== Recent Errors ==="

# Backend errors (last 5)
echo "Backend:"
tail -5 automation-webapp-be/logs/error.log 2> /dev/null || echo "  No error log"

# Native App errors (last 5)
echo "Native App:"
tail -5 beena-native-app/beenanativeapp/logs/error.log 2> /dev/null || echo "  No error log"
```

### Error Origin Matrix

| Symptom                     | Check First            | Then Check             | Likely Cause              |
| --------------------------- | ---------------------- | ---------------------- | ------------------------- |
| "Network Error" in Frontend | Browser Network tab    | Backend logs           | CORS or Backend down      |
| 401 Unauthorized            | Backend JWT validation | Frontend token storage | Expired/invalid token     |
| OAuth callback fails        | Backend OAuth logs     | Provider dashboard     | Redirect URI mismatch     |
| Payment validation fails    | Backend Stripe logs    | Native App logs        | Invalid payment_intent_id |
| Migration hangs             | Native App logs        | Playwright browser     | Selector timeout          |
| "Connection refused"        | Target service status  | Firewall/ports         | Service not running       |

## Step 2: Log Correlation

### Adding Correlation IDs

#### Frontend (Request Interceptor)

**src/services/api.ts**:

```typescript
import axios from "axios";
import { v4 as uuidv4 } from "uuid";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

// Add correlation ID to every request
api.interceptors.request.use((config) => {
  const correlationId = uuidv4();
  config.headers["X-Correlation-ID"] = correlationId;

  // Log for debugging
  console.log(
    `[${correlationId}] ${config.method?.toUpperCase()} ${config.url}`,
  );

  return config;
});

api.interceptors.response.use(
  (response) => {
    const correlationId = response.config.headers["X-Correlation-ID"];
    console.log(`[${correlationId}] Response: ${response.status}`);
    return response;
  },
  (error) => {
    const correlationId = error.config?.headers?.["X-Correlation-ID"];
    console.error(`[${correlationId}] Error:`, error.message);
    throw error;
  },
);
```

#### Backend (Middleware)

**src/interfaces/http/middlewares/correlationId.js**:

```javascript
const { v4: uuidv4 } = require("uuid");

module.exports = function correlationIdMiddleware(req, res, next) {
  // Use existing ID from Frontend or generate new one
  req.correlationId = req.headers["x-correlation-id"] || uuidv4();

  // Add to response headers
  res.setHeader("X-Correlation-ID", req.correlationId);

  // Add to logger context
  req.logger = require("../../../infrastructure/logging/logger").child({
    correlationId: req.correlationId,
    path: req.path,
    method: req.method,
  });

  next();
};
```

#### Native App (Middleware)

**beenanativeapp/src/beenanativeapp/api/middleware/correlation.py**:

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
import logging

logger = logging.getLogger(__name__)

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get or generate correlation ID
        correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))

        # Store in request state
        request.state.correlation_id = correlation_id

        # Add to logging context
        logger.info(
            f"[{correlation_id}] {request.method} {request.url.path}",
            extra={'correlation_id': correlation_id}
        )

        # Process request
        response = await call_next(request)

        # Add to response
        response.headers['X-Correlation-ID'] = correlation_id

        return response
```

### Finding Correlated Logs

```bash
# Search all logs for a correlation ID
CORR_ID="abc123-def456"

echo "=== Frontend (Browser Console) ==="
echo "Search: [$CORR_ID]"

echo ""
echo "=== Backend ==="
grep "$CORR_ID" automation-webapp-be/logs/*.log

echo ""
echo "=== Native App ==="
grep "$CORR_ID" beena-native-app/beenanativeapp/logs/*.log
```

## Step 3: Common Cross-Service Failures

### OAuth Flow Failures

```
Frontend → Backend → Klaviyo
   │          │         │
   │          │         └── 4. Returns tokens
   │          │
   │          └── 3. Exchanges code for tokens
   │
   └── 1. Initiates OAuth
         2. User authorizes at Klaviyo
```

**Debugging Steps**:

1. **Frontend Console**: Check if redirect URL is correct

   ```javascript
   console.log("OAuth URL:", authorizationUrl);
   ```

2. **Backend Logs**: Look for PKCE/state validation errors

   ```bash
   grep -E "(OAuth|PKCE|state|token)" automation-webapp-be/logs/combined.log | tail -20
   ```

3. **Common Fixes**:
   - Redirect URI mismatch → Check Klaviyo dashboard settings
   - State invalid → OAuthState expired (>10 min) or CORS issue
   - Token exchange fails → Check client_secret in .env

### Payment Validation Failures

```
Frontend → Native App → Backend → Stripe
   │            │           │        │
   │            │           │        └── 4. Returns payment status
   │            │           │
   │            │           └── 3. Validates with Stripe API
   │            │
   │            └── 2. Calls /api/v1/payments/validate
   │
   └── 1. Starts migration with payment_intent_id
```

**Debugging Steps**:

1. **Frontend**: Verify payment_intent_id is being sent

   ```typescript
   console.log("Starting migration with:", { payment_intent_id });
   ```

2. **Native App**: Check validation request

   ```bash
   grep "payment" beena-native-app/beenanativeapp/logs/*.log | tail -10
   ```

3. **Backend**: Check Stripe API response

   ```bash
   grep -E "(payment|stripe|pi_)" automation-webapp-be/logs/combined.log | tail -10
   ```

4. **Common Fixes**:
   - 402 Payment Required → Payment not succeeded, check Stripe dashboard
   - Network error → BACKEND_API_URL incorrect in Native App .env
   - Timeout → Backend or Stripe slow, check connection

### Migration Execution Failures

```
Frontend → Native App → Playwright → Source Platform
   │            │            │              │
   │            │            │              └── 4. Scrapes/extracts data
   │            │            │
   │            │            └── 3. Automates browser
   │            │
   │            └── 2. Executes job
   │
   └── 1. Submits automation job
```

**Debugging Steps**:

1. **Frontend**: Check job status polling

   ```typescript
   // In DevTools Network tab, filter by "status"
   ```

2. **Native App Logs**: Look for Playwright errors

   ```bash
   grep -E "(Playwright|selector|timeout|error)" beena-native-app/beenanativeapp/logs/*.log | tail -20
   ```

3. **Browser State**: Check if browser is visible (headless=false)

   ```python
   # In custom_functions, add:
   await page.screenshot(path=f"debug_{step_name}.png")
   ```

4. **Common Fixes**:
   - Selector timeout → Platform UI changed, update selectors
   - Navigation timeout → Network slow or page taking long
   - Element not found → Check if logged in, iframe context

## Step 4: Service-Specific Debugging

### Frontend Debugging

```typescript
// Enable verbose logging
localStorage.setItem("debug", "*");

// Check environment variables
console.log("API URL:", import.meta.env.VITE_API_URL);
console.log("Python API:", import.meta.env.VITE_PYTHON_API_URL);

// Monitor all API calls
axios.interceptors.request.use((config) => {
  console.group(`API: ${config.method?.toUpperCase()} ${config.url}`);
  console.log("Headers:", config.headers);
  console.log("Data:", config.data);
  console.groupEnd();
  return config;
});
```

### Backend Debugging

```javascript
// Enable debug logging
// Set in .env: LOG_LEVEL=debug

// Add request body logging
app.use((req, res, next) => {
  if (process.env.DEBUG_REQUESTS === "true") {
    console.log("Request:", {
      method: req.method,
      path: req.path,
      body: req.body,
      query: req.query,
      headers: req.headers,
    });
  }
  next();
});

// Log MongoDB queries
mongoose.set("debug", true);
```

### Native App Debugging

```python
# Enable verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Add request logging
from fastapi import Request

@app.middleware("http")
async def log_requests(request: Request, call_next):
    body = await request.body()
    print(f"Request: {request.method} {request.url}")
    print(f"Body: {body.decode()}")

    response = await call_next(request)
    return response

# Playwright debug mode
import os
os.environ['PWDEBUG'] = '1'  # Opens Playwright Inspector
```

## Step 5: Request Tracing Template

Use this template to trace a request through all services:

````markdown
## Request Trace: [ISSUE DESCRIPTION]

### Correlation ID: [ID]

### 1. Frontend

- **Action**: [What user did]
- **Request**: [Method] [URL]
- **Payload**: ```json
  {}
````

- **Console Output**:
- **Network Tab**: [Status code, timing]

### 2. Backend

- **Received**: [Timestamp]
- **Log entries**:
  ```
  [paste relevant logs]
  ```
- **Database operations**:
- **External API calls**:
- **Response sent**: [Status, body summary]

### 3. Native App (if applicable)

- **Received**: [Timestamp]
- **Job ID**: [ID]
- **Log entries**:
  ```
  [paste relevant logs]
  ```
- **Playwright actions**:
- **Response/Result**:

### Root Cause

[What actually went wrong]

### Resolution

[How it was fixed]

````

## Quick Reference Commands

### Check All Logs

```bash
# Tail all service logs simultaneously
# Terminal 1 - Backend
tail -f automation-webapp-be/logs/combined.log

# Terminal 2 - Native App
tail -f beena-native-app/beenanativeapp/logs/app.log

# Terminal 3 - Frontend (Browser Console)
# Open DevTools → Console
````

### Test Service Connectivity

```bash
# Frontend → Backend
curl http://localhost:5001/api/v1/health

# Frontend → Native App
curl http://localhost:8000/health

# Native App → Backend
curl http://localhost:5001/api/v1/payments/validate \
  -H "Content-Type: application/json" \
  -d '{"payment_intent_id": "pi_test123"}'
```

### Check Environment Variables

```bash
# Backend
node -e "console.log(require('./src/infrastructure/config'))"

# Native App
python -c "from beenanativeapp.config import settings; print(vars(settings))"

# Frontend (in browser console)
Object.keys(import.meta.env).filter(k => k.startsWith('VITE_'))
```

## Best Practices

1. **Always check the simplest things first**: Is the service running? Is the port correct?
2. **Use correlation IDs** to trace requests across services
3. **Check logs in order of request flow**: Frontend → Backend → Native App
4. **Reproduce in isolation** when possible
5. **Add temporary logging** rather than guessing
6. **Check environment variables** match between services
7. **Verify network connectivity** between services
8. **Document findings** for future reference
9. **Use screenshots/recordings** for hard-to-reproduce issues
10. **Check for recent changes** in all affected services
