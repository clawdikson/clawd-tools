# debugging-oauth-integration

## Description

Debug OAuth 2.0 integration issues in the Beena automation platform, specifically focusing on Klaviyo OAuth with PKCE flow. Covers common OAuth errors, state validation failures, token refresh issues, and debugging techniques for full-stack OAuth flows.

## When to Use

- OAuth connection failing or hanging
- "Invalid or expired state parameter" errors
- Token refresh failures ("invalid_grant")
- Users unable to connect Klaviyo account
- OAuth callback not triggering or redirecting incorrectly
- Token encryption/decryption errors
- Missing or misconfigured environment variables
- Testing OAuth flow in development or staging

## Prerequisites

- Understanding of OAuth 2.0 Authorization Code Flow with PKCE
- Familiarity with Klaviyo OAuth implementation (see `docs/KLAVIYO_OAUTH_INTEGRATION.md`)
- Knowledge of the backend OAuth services (`src/application/services/oauth/`)
- Access to application logs and database

## Key Concepts

### OAuth Flow Overview

The Klaviyo integration uses OAuth 2.0 Authorization Code Flow with PKCE:

1. **Initiate** → Generate PKCE pair, create state, redirect to Klaviyo
2. **Authorize** → User logs in and approves permissions
3. **Callback** → Validate state, exchange code for tokens
4. **Store** → Encrypt and save tokens in database
5. **Refresh** → Automatic refresh before expiration (10 min window)

### Components Involved

**Backend** (`automation-webapp-be`):

- `KlaviyoOAuthService.js` - OAuth logic
- `PKCEGenerator.js` - PKCE code generation
- `TokenEncryption.js` - AES-256 token encryption
- `OAuthConnection` model - Token storage
- `OAuthState` model - Temporary state storage (5 min TTL)
- `oauthTokenRefresh.js` - Automatic refresh job (every 5 min)

**Frontend** (`automation-webapp-fe`):

- `/integrations/klaviyo/install.tsx` - Entry point
- `/integrations/klaviyo/callback.tsx` - Callback handler
- `/integrations/klaviyo/success.tsx` - Success page
- `/integrations/klaviyo/error.tsx` - Error page

## Common OAuth Errors

### 1. "Invalid or expired state parameter"

**Cause**: State parameter validation failed or expired (>5 min)

**Debug Steps**:

```javascript
// Check state in database
const OAuthState = require("./models/oauthState");

async function debugState(state) {
  const stateRecord = await OAuthState.findOne({ state });

  if (!stateRecord) {
    console.log("❌ State not found in database");
    return;
  }

  console.log("State record:", {
    state: stateRecord.state,
    userId: stateRecord.userId,
    provider: stateRecord.provider,
    createdAt: stateRecord.createdAt,
    expiresAt: stateRecord.expiresAt,
    isExpired: stateRecord.expiresAt < new Date(),
    isUsed: stateRecord.used,
  });
}
```

**Solutions**:

- **If expired**: User took >5 minutes to authorize. Restart OAuth flow.
- **If used**: State was already consumed. Restart OAuth flow.
- **If not found**: State was never created or database issue. Check logs for errors during initiation.

### 2. "Authorization code expired"

**Cause**: Code wasn't exchanged within Klaviyo's expiration window (typically 5 minutes)

**Debug Steps**:

```javascript
// In callback handler, add timing debug
console.log("OAuth Callback Debug:", {
  timestamp: new Date().toISOString(),
  code: code ? "Present" : "Missing",
  state: state ? "Present" : "Missing",
  codeLength: code?.length,
  stateLength: state?.length,
});
```

**Solutions**:

- Check for network issues causing slow redirects
- Verify callback URL is reachable from Klaviyo
- Ensure no middleware is blocking/delaying the callback handler

### 3. "Refresh token invalid" or "invalid_grant"

**Cause**: App was uninstalled from Klaviyo, token not used for 90 days, or token was revoked

**Debug Steps**:

```javascript
// Check token refresh errors in logs
// In KlaviyoOAuthService.js refreshAccessToken method:

async refreshAccessToken(userId) {
  try {
    // ... existing code ...

    const response = await axios.post(this.tokenBaseUrl, params);
    console.log('✅ Token refresh successful');

  } catch (error) {
    console.error('❌ Token refresh failed:', {
      status: error.response?.status,
      error: error.response?.data?.error,
      errorDescription: error.response?.data?.error_description,
      userId,
      connectionId: connection._id
    });

    if (error.response?.data?.error === 'invalid_grant') {
      console.log('🔴 Connection revoked - user needs to reconnect');
      // Mark connection as invalid
      await connection.updateOne({ isValid: false });
    }

    throw error;
  }
}
```

**Solutions**:

- **If invalid_grant**: Connection was revoked. User must reconnect:
  ```javascript
  // Frontend - show reconnect prompt
  if (error.response?.data?.error === "invalid_grant") {
    setShowReconnectPrompt(true);
  }
  ```
- Check if app was uninstalled from Klaviyo account
- Verify token wasn't manually revoked in database

### 4. "Encryption key not found"

**Cause**: `OAUTH_ENCRYPTION_KEY` not set in environment

**Debug Steps**:

```javascript
// In TokenEncryption.js
class TokenEncryption {
  constructor() {
    const key = process.env.OAUTH_ENCRYPTION_KEY;

    if (!key) {
      console.error("❌ OAUTH_ENCRYPTION_KEY not set");
      console.log(
        "Generate one with: node -e \"console.log(require('crypto').randomBytes(16).toString('hex'))\"",
      );
      throw new Error("OAUTH_ENCRYPTION_KEY is required");
    }

    if (key.length !== 32) {
      console.error("❌ OAUTH_ENCRYPTION_KEY must be 32 characters");
      console.log("Current length:", key.length);
      throw new Error("OAUTH_ENCRYPTION_KEY must be 32 characters");
    }

    console.log("✅ OAUTH_ENCRYPTION_KEY configured");
  }
}
```

**Solutions**:

- Add to `.env`:
  ```bash
  OAUTH_ENCRYPTION_KEY=$(node -e "console.log(require('crypto').randomBytes(16).toString('hex'))")
  ```
- Verify `.env` file is loaded (check `require('dotenv').config()`)
- Restart server after adding key

### 5. "Redirect URI mismatch"

**Cause**: Redirect URI in request doesn't match Klaviyo app configuration

**Debug Steps**:

```javascript
// Log redirect URI comparison
console.log("Redirect URI Debug:", {
  configured: process.env.KLAVIYO_REDIRECT_URI,
  used: this.redirectUri,
  klaviyoConfig: "Check Klaviyo app settings",
});

// In Klaviyo app settings, verify:
// Development: http://localhost:3001/api/v1/oauth/klaviyo/callback
// Production: https://yourapp.com/api/v1/oauth/klaviyo/callback
```

**Solutions**:

- Verify `KLAVIYO_REDIRECT_URI` in `.env` matches Klaviyo app settings exactly
- Use correct protocol (http for dev, https for prod)
- Include full path: `/api/v1/oauth/klaviyo/callback`
- No trailing slashes

### 6. Callback Not Triggered

**Cause**: Frontend not properly handling callback or redirect

**Debug Steps**:

```typescript
// Frontend: /integrations/klaviyo/callback.tsx
useEffect(() => {
  console.log("Callback page loaded:", {
    url: window.location.href,
    search: window.location.search,
    code: searchParams.get("code"),
    state: searchParams.get("state"),
    error: searchParams.get("error"),
    errorDescription: searchParams.get("error_description"),
  });

  // Check if Klaviyo returned error
  const error = searchParams.get("error");
  if (error) {
    console.error("OAuth error from Klaviyo:", {
      error,
      description: searchParams.get("error_description"),
    });
  }
}, []);
```

**Solutions**:

- Verify callback route is registered: `/integrations/klaviyo/callback`
- Check browser console for JavaScript errors
- Ensure no ad blockers are interfering
- Verify Klaviyo app has correct redirect URI

## Debugging Techniques

### 1. Enable Debug Logging

Add comprehensive logging to OAuth flow:

```javascript
// KlaviyoOAuthService.js - Add at key points

async initiateOAuth(userId, options) {
  console.log('🔵 [OAuth] Initiating flow:', { userId, options });

  const { codeVerifier, codeChallenge } = PKCEGenerator.generatePKCEPair();
  console.log('🔑 [OAuth] PKCE generated:', {
    verifierLength: codeVerifier.length,
    challengeLength: codeChallenge.length
  });

  const state = PKCEGenerator.generateState();
  console.log('📝 [OAuth] State created:', state);

  await stateRecord.save();
  console.log('✅ [OAuth] State saved to DB');

  console.log('🔗 [OAuth] Authorization URL:', authorizationUrl);

  return { authorizationUrl, state };
}

async exchangeCodeForTokens(code, state, userId) {
  console.log('🔵 [OAuth] Exchanging code:', { state, userId, codeLength: code?.length });

  const stateRecord = await OAuthState.findValidState(state);
  if (!stateRecord) {
    console.error('❌ [OAuth] State validation failed');
    throw new Error('Invalid or expired state parameter');
  }
  console.log('✅ [OAuth] State validated');

  // Exchange code for tokens
  const response = await axios.post(this.tokenBaseUrl, params);
  console.log('✅ [OAuth] Tokens received:', {
    hasAccessToken: !!response.data.access_token,
    hasRefreshToken: !!response.data.refresh_token,
    expiresIn: response.data.expires_in
  });

  // Encrypt tokens
  const encryptedAccessToken = TokenEncryption.encrypt(response.data.access_token);
  console.log('🔒 [OAuth] Tokens encrypted');

  // Save connection
  await connection.save();
  console.log('✅ [OAuth] Connection saved');

  return connection;
}
```

### 2. Test OAuth Flow with curl

Test token exchange manually:

```bash
# 1. Get authorization code (do this in browser)
# Navigate to authorization URL from logs

# 2. Exchange code for tokens
curl -X POST https://a.klaviyo.com/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "client_id=${KLAVIYO_CLIENT_ID}" \
  -d "client_secret=${KLAVIYO_CLIENT_SECRET}" \
  -d "code=${AUTH_CODE}" \
  -d "redirect_uri=${KLAVIYO_REDIRECT_URI}" \
  -d "code_verifier=${CODE_VERIFIER}"

# 3. Test refresh token
curl -X POST https://a.klaviyo.com/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "client_id=${KLAVIYO_CLIENT_ID}" \
  -d "client_secret=${KLAVIYO_CLIENT_SECRET}" \
  -d "refresh_token=${REFRESH_TOKEN}"
```

### 3. Database Inspection

Check OAuth state and connections:

```javascript
// MongoDB queries

// Check recent OAuth states
db.oauthstates.find().sort({ createdAt: -1 }).limit(5);

// Check expired states
db.oauthstates.find({ expiresAt: { $lt: new Date() } });

// Check used states
db.oauthstates.find({ used: true });

// Check OAuth connections for user
db.oauthconnections.find({ userId: ObjectId("USER_ID") });

// Check connections needing refresh
db.oauthconnections.find({
  provider: "klaviyo",
  tokenExpiresAt: { $lt: new Date(Date.now() + 10 * 60 * 1000) },
});

// Check invalid connections
db.oauthconnections.find({ isValid: false });
```

### 4. Network Debugging

Use browser DevTools or Charles Proxy:

```javascript
// Frontend - Log all OAuth-related requests
axios.interceptors.request.use((request) => {
  if (request.url.includes("oauth") || request.url.includes("klaviyo")) {
    console.log("📤 OAuth Request:", {
      method: request.method,
      url: request.url,
      headers: request.headers,
      data: request.data,
    });
  }
  return request;
});

axios.interceptors.response.use(
  (response) => {
    if (response.config.url.includes("oauth")) {
      console.log("📥 OAuth Response:", {
        status: response.status,
        url: response.config.url,
        data: response.data,
      });
    }
    return response;
  },
  (error) => {
    if (error.config?.url.includes("oauth")) {
      console.error("❌ OAuth Error:", {
        status: error.response?.status,
        url: error.config.url,
        error: error.response?.data,
      });
    }
    return Promise.reject(error);
  },
);
```

### 5. PKCE Validation

Verify PKCE code generation:

```javascript
// Test PKCE generator
const PKCEGenerator = require("./PKCEGenerator");

function testPKCE() {
  const { codeVerifier, codeChallenge } = PKCEGenerator.generatePKCEPair();

  console.log("PKCE Test:", {
    verifier: codeVerifier,
    verifierLength: codeVerifier.length,
    challenge: codeChallenge,
    challengeLength: codeChallenge.length,
    isValid: codeVerifier.length === 128 && codeChallenge.length === 43,
  });

  // Manually verify challenge
  const crypto = require("crypto");
  const expectedChallenge = crypto
    .createHash("sha256")
    .update(codeVerifier)
    .digest("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");

  console.log("Challenge verification:", {
    generated: codeChallenge,
    expected: expectedChallenge,
    matches: codeChallenge === expectedChallenge,
  });
}

testPKCE();
```

## Environment Configuration Checklist

Verify all OAuth environment variables are set:

```bash
# Backend .env
KLAVIYO_CLIENT_ID=your-client-id
KLAVIYO_CLIENT_SECRET=your-client-secret
KLAVIYO_REDIRECT_URI=http://localhost:3001/api/v1/oauth/klaviyo/callback
OAUTH_ENCRYPTION_KEY=32-character-encryption-key

# Verify in Node.js
console.log('OAuth Config:', {
  clientId: process.env.KLAVIYO_CLIENT_ID ? '✅ Set' : '❌ Missing',
  clientSecret: process.env.KLAVIYO_CLIENT_SECRET ? '✅ Set' : '❌ Missing',
  redirectUri: process.env.KLAVIYO_REDIRECT_URI || '⚠️  Using default',
  encryptionKey: process.env.OAUTH_ENCRYPTION_KEY?.length === 32 ? '✅ Valid' : '❌ Invalid'
});
```

## Testing OAuth Flow

### Manual Test Procedure

1. **Clear existing connections**:

   ```javascript
   // In database or via API
   db.oauthconnections.deleteMany({ userId: ObjectId("TEST_USER_ID") });
   db.oauthstates.deleteMany({ userId: ObjectId("TEST_USER_ID") });
   ```

2. **Initiate connection**:
   - Navigate to Integrations page
   - Click "Connect with Klaviyo"
   - Verify authorization URL in logs
   - Check state saved in database

3. **Authorize in Klaviyo**:
   - Log in to Klaviyo (if needed)
   - Review permissions
   - Click "Approve"
   - Monitor for redirect

4. **Verify callback**:
   - Check callback page loads
   - Verify code and state in URL
   - Check backend logs for token exchange
   - Verify connection saved in database

5. **Test API access**:
   ```javascript
   // Make authenticated request to Klaviyo API
   const response = await api.get("/v1/oauth/klaviyo/status");
   console.log("Connection status:", response.data);
   ```

### Automated Test Script

```javascript
// tests/integration/oauth.test.js
describe("Klaviyo OAuth Flow", () => {
  it("should complete full OAuth flow", async () => {
    // 1. Initiate
    const initiateResponse = await request(app)
      .post("/api/v1/oauth/klaviyo/connect")
      .set("Authorization", `Bearer ${testUserToken}`)
      .send({ redirectUri: "http://localhost:3000/callback" });

    expect(initiateResponse.status).toBe(200);
    expect(initiateResponse.body.authorizationUrl).toContain(
      "klaviyo.com/oauth/authorize",
    );
    const state = new URL(
      initiateResponse.body.authorizationUrl,
    ).searchParams.get("state");

    // 2. Verify state in database
    const stateRecord = await OAuthState.findOne({ state });
    expect(stateRecord).toBeDefined();
    expect(stateRecord.userId.toString()).toBe(testUserId);

    // 3. Simulate callback (requires test access token from Klaviyo)
    // This part typically requires manual intervention or Klaviyo test credentials

    // 4. Verify connection status
    const statusResponse = await request(app)
      .get("/api/v1/oauth/klaviyo/status")
      .set("Authorization", `Bearer ${testUserToken}`);

    expect(statusResponse.status).toBe(200);
    expect(statusResponse.body.connected).toBe(true);
  });
});
```

## Troubleshooting Checklist

When OAuth fails, go through this checklist:

- [ ] **Environment variables set**: Check all required OAuth env vars
- [ ] **Klaviyo app configured**: Verify client ID, secret, redirect URI
- [ ] **Database accessible**: Test MongoDB connection
- [ ] **State not expired**: OAuth state has 5-minute TTL
- [ ] **Code not reused**: Authorization codes are single-use
- [ ] **Redirect URI matches**: Exact match with Klaviyo app settings
- [ ] **HTTPS in production**: Klaviyo requires HTTPS for production redirects
- [ ] **Encryption key valid**: Must be 32 characters
- [ ] **Token refresh job running**: Background job refreshes tokens every 5 min
- [ ] **Network connectivity**: Backend can reach Klaviyo APIs
- [ ] **CORS configured**: Frontend can call backend OAuth endpoints
- [ ] **Error logs checked**: Review logs for specific error messages

## Production Monitoring

Set up monitoring for OAuth issues:

```javascript
// Add metrics to OAuth operations
const metrics = {
  oauthInitiations: 0,
  oauthSuccesses: 0,
  oauthFailures: 0,
  tokenRefreshes: 0,
  tokenRefreshFailures: 0
};

// In KlaviyoOAuthService
async initiateOAuth(userId, options) {
  metrics.oauthInitiations++;
  try {
    // ... existing code ...
    return result;
  } catch (error) {
    metrics.oauthFailures++;
    throw error;
  }
}

async exchangeCodeForTokens(code, state, userId) {
  try {
    // ... existing code ...
    metrics.oauthSuccesses++;
    return connection;
  } catch (error) {
    metrics.oauthFailures++;
    throw error;
  }
}

// Expose metrics endpoint
app.get('/metrics/oauth', (req, res) => {
  res.json({
    ...metrics,
    successRate: metrics.oauthInitiations > 0
      ? (metrics.oauthSuccesses / metrics.oauthInitiations * 100).toFixed(2) + '%'
      : 'N/A'
  });
});
```

## Related Files

- `docs/KLAVIYO_OAUTH_INTEGRATION.md` - Complete OAuth integration guide
- `src/application/services/oauth/KlaviyoOAuthService.js` - Main OAuth service
- `src/application/services/oauth/PKCEGenerator.js` - PKCE code generation
- `src/application/services/oauth/TokenEncryption.js` - Token encryption
- `src/infrastructure/database/mongodb/models/oauthConnection.js` - Connection model
- `src/infrastructure/database/mongodb/models/oauthState.js` - State model
- `src/infrastructure/jobs/oauthTokenRefresh.js` - Automatic token refresh
- `frontend/src/pages/integrations/klaviyo/callback.tsx` - Frontend callback handler

## References

- [OAuth 2.0 Specification](https://datatracker.ietf.org/doc/html/rfc6749)
- [PKCE Specification (RFC 7636)](https://datatracker.ietf.org/doc/html/rfc7636)
- [Klaviyo OAuth Documentation](https://developers.klaviyo.com/en/docs/integrate_with_klaviyo#oauth)
- [OAuth Debugging Guide](https://www.oauth.com/oauth2-servers/debugging/)
