---
name: implementing-oauth-flows
description: Implement OAuth 2.0 integrations with PKCE in the Node.js/Express backend. Covers token encryption, refresh logic, service layer abstraction, and Clean Architecture patterns. Use when adding new third-party service integrations like Klaviyo, Mailchimp, or Stripe.
---

# Implementing OAuth Flows

Add OAuth 2.0 provider integrations to the automation backend following Clean Architecture principles. This skill covers PKCE flow, token management, encryption, and the project's service layer patterns.

## When to Use This Skill

- Adding new OAuth provider integrations (Klaviyo, Mailchimp, Shopify, etc.)
- Implementing token refresh logic
- Setting up token encryption and secure storage
- Creating API proxy endpoints for OAuth-protected services
- Debugging OAuth authentication issues

## OAuth Architecture Overview

### Project Structure

```
src/
├── application/
│   ├── services/
│   │   └── oauthService.js          # Service abstraction layer
│   └── useCases/
│       └── oauth/
│           ├── initiateOAuth.js      # Start OAuth flow
│           ├── handleCallback.js     # Process OAuth callback
│           └── refreshToken.js       # Token refresh logic
├── infrastructure/
│   ├── database/mongodb/models/
│   │   ├── OAuthConnection.js        # Token storage model
│   │   └── OAuthState.js             # PKCE state model
│   └── jobs/
│       └── oauthTokenRefresh.js      # Background token refresh
└── interfaces/http/
    ├── controllers/
    │   └── oauthController.js         # HTTP handlers
    └── routes/
        └── oauth.js                   # Route definitions
```

### Flow Diagram

```
Frontend                    Backend                     OAuth Provider
   |                           |                              |
   |--1. Initiate OAuth------->|                              |
   |                           |--2. Generate PKCE----------->|
   |                           |    (code_verifier + challenge)
   |<--3. Redirect URL---------|                              |
   |                                                          |
   |--4. User authorizes---------------------------------->|
   |                                                          |
   |<--5. Callback with code--------------------------------|
   |                           |                              |
   |--6. Send code------------>|                              |
   |                           |--7. Exchange code + verifier->
   |                           |<--8. Access & Refresh tokens-|
   |                           |                              |
   |                           |--9. Encrypt & store--------->|
   |<--10. Success response----|        (MongoDB)            |
```

## Step 1: Environment Configuration

### Add OAuth Credentials

**.env file**:

```bash
# OAuth Provider (e.g., Klaviyo)
KLAVIYO_CLIENT_ID=your_client_id_here
KLAVIYO_CLIENT_SECRET=your_client_secret_here
KLAVIYO_REDIRECT_URI=http://localhost:3000/integrations/klaviyo/callback

# Token encryption (MUST be 32 characters)
OAUTH_ENCRYPTION_KEY=your-32-character-encryption-key

# Frontend URL for redirects
FRONTEND_URL=http://localhost:3000
```

### Config File

**src/infrastructure/config/index.js**:

```javascript
module.exports = {
  oauth: {
    klaviyo: {
      clientId: process.env.KLAVIYO_CLIENT_ID,
      clientSecret: process.env.KLAVIYO_CLIENT_SECRET,
      redirectUri: process.env.KLAVIYO_REDIRECT_URI,
      authorizationEndpoint: "https://www.klaviyo.com/oauth/authorize",
      tokenEndpoint: "https://a.klaviyo.com/oauth/token",
      scopes: [
        "campaigns:read",
        "campaigns:write",
        "flows:read",
        "flows:write",
      ],
    },
    encryptionKey: process.env.OAUTH_ENCRYPTION_KEY,
  },
};
```

## Step 2: Database Models

### OAuthConnection Model

**src/infrastructure/database/mongodb/models/OAuthConnection.js**:

```javascript
const mongoose = require("mongoose");
const crypto = require("crypto");
const config = require("../../../config");

const oauthConnectionSchema = new mongoose.Schema(
  {
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      index: true,
    },
    provider: {
      type: String,
      required: true,
      enum: ["klaviyo", "mailchimp", "shopify"],
      index: true,
    },
    accessToken: {
      type: String,
      required: true,
    },
    refreshToken: {
      type: String,
      required: true,
    },
    expiresAt: {
      type: Date,
      required: true,
      index: true, // For token refresh job
    },
    scope: {
      type: [String],
      default: [],
    },
    metadata: {
      type: mongoose.Schema.Types.Mixed,
      default: {},
    },
  },
  {
    timestamps: true,
  },
);

// Compound index for user + provider uniqueness
oauthConnectionSchema.index({ userId: 1, provider: 1 }, { unique: true });

// Encryption helpers
function encrypt(text) {
  const algorithm = "aes-256-cbc";
  const key = Buffer.from(config.oauth.encryptionKey, "utf8");
  const iv = crypto.randomBytes(16);

  const cipher = crypto.createCipheriv(algorithm, key, iv);
  let encrypted = cipher.update(text, "utf8", "hex");
  encrypted += cipher.final("hex");

  return iv.toString("hex") + ":" + encrypted;
}

function decrypt(text) {
  const algorithm = "aes-256-cbc";
  const key = Buffer.from(config.oauth.encryptionKey, "utf8");

  const parts = text.split(":");
  const iv = Buffer.from(parts.shift(), "hex");
  const encrypted = parts.join(":");

  const decipher = crypto.createDecipheriv(algorithm, key, iv);
  let decrypted = decipher.update(encrypted, "hex", "utf8");
  decrypted += decipher.final("utf8");

  return decrypted;
}

// Encrypt tokens before saving
oauthConnectionSchema.pre("save", function (next) {
  if (this.isModified("accessToken")) {
    this.accessToken = encrypt(this.accessToken);
  }
  if (this.isModified("refreshToken")) {
    this.refreshToken = encrypt(this.refreshToken);
  }
  next();
});

// Method to get decrypted tokens
oauthConnectionSchema.methods.getDecryptedTokens = function () {
  return {
    accessToken: decrypt(this.accessToken),
    refreshToken: decrypt(this.refreshToken),
  };
};

module.exports = mongoose.model("OAuthConnection", oauthConnectionSchema);
```

### OAuthState Model (PKCE)

**src/infrastructure/database/mongodb/models/OAuthState.js**:

```javascript
const mongoose = require("mongoose");

const oauthStateSchema = new mongoose.Schema(
  {
    state: {
      type: String,
      required: true,
      unique: true,
      index: true,
    },
    codeVerifier: {
      type: String,
      required: true,
    },
    provider: {
      type: String,
      required: true,
    },
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
    },
    expiresAt: {
      type: Date,
      required: true,
      default: () => new Date(Date.now() + 10 * 60 * 1000), // 10 minutes
      index: true,
    },
  },
  {
    timestamps: true,
  },
);

// Auto-delete expired states
oauthStateSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });

module.exports = mongoose.model("OAuthState", oauthStateSchema);
```

## Step 3: PKCE Implementation

### Generate PKCE Challenge

**src/application/services/oauthService.js**:

```javascript
const crypto = require("crypto");

class OAuthService {
  /**
   * Generate PKCE code verifier and challenge
   */
  static generatePKCE() {
    // Generate random code verifier (43-128 characters)
    const codeVerifier = crypto.randomBytes(32).toString("base64url");

    // Generate code challenge (SHA256 hash of verifier)
    const codeChallenge = crypto
      .createHash("sha256")
      .update(codeVerifier)
      .digest("base64url");

    return {
      codeVerifier,
      codeChallenge,
    };
  }

  /**
   * Generate state parameter (CSRF protection)
   */
  static generateState() {
    return crypto.randomBytes(16).toString("hex");
  }
}

module.exports = OAuthService;
```

## Step 4: Initiate OAuth Flow

### Use Case

**src/application/useCases/oauth/initiateOAuth.js**:

```javascript
const OAuthState = require("../../../infrastructure/database/mongodb/models/OAuthState");
const OAuthService = require("../../services/oauthService");
const config = require("../../../infrastructure/config");

module.exports = async function initiateOAuth({ userId, provider }) {
  // Generate PKCE parameters
  const { codeVerifier, codeChallenge } = OAuthService.generatePKCE();
  const state = OAuthService.generateState();

  // Store state in database
  await OAuthState.create({
    state,
    codeVerifier,
    provider,
    userId,
  });

  // Get provider configuration
  const providerConfig = config.oauth[provider];

  // Build authorization URL
  const authUrl = new URL(providerConfig.authorizationEndpoint);
  authUrl.searchParams.append("client_id", providerConfig.clientId);
  authUrl.searchParams.append("redirect_uri", providerConfig.redirectUri);
  authUrl.searchParams.append("response_type", "code");
  authUrl.searchParams.append("scope", providerConfig.scopes.join(" "));
  authUrl.searchParams.append("state", state);
  authUrl.searchParams.append("code_challenge", codeChallenge);
  authUrl.searchParams.append("code_challenge_method", "S256");

  return {
    authorizationUrl: authUrl.toString(),
    state,
  };
};
```

### Controller

**src/interfaces/http/controllers/oauthController.js**:

```javascript
const initiateOAuth = require("../../../application/useCases/oauth/initiateOAuth");

exports.initiateOAuth = async (req, res, next) => {
  try {
    const { provider } = req.params;
    const userId = req.user.id;

    const result = await initiateOAuth({ userId, provider });

    res.json({
      success: true,
      data: result,
    });
  } catch (error) {
    next(error);
  }
};
```

## Step 5: Handle OAuth Callback

### Use Case

**src/application/useCases/oauth/handleCallback.js**:

```javascript
const axios = require("axios");
const OAuthState = require("../../../infrastructure/database/mongodb/models/OAuthState");
const OAuthConnection = require("../../../infrastructure/database/mongodb/models/OAuthConnection");
const config = require("../../../infrastructure/config");

module.exports = async function handleCallback({ code, state, provider }) {
  // Verify state parameter
  const oauthState = await OAuthState.findOne({ state, provider });

  if (!oauthState) {
    throw new Error("Invalid or expired OAuth state");
  }

  if (oauthState.expiresAt < new Date()) {
    await OAuthState.deleteOne({ _id: oauthState._id });
    throw new Error("OAuth state expired");
  }

  const providerConfig = config.oauth[provider];

  // Exchange code for tokens
  const tokenResponse = await axios.post(
    providerConfig.tokenEndpoint,
    {
      grant_type: "authorization_code",
      code,
      redirect_uri: providerConfig.redirectUri,
      client_id: providerConfig.clientId,
      client_secret: providerConfig.clientSecret,
      code_verifier: oauthState.codeVerifier, // PKCE verification
    },
    {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    },
  );

  const { access_token, refresh_token, expires_in, scope } = tokenResponse.data;

  // Calculate expiration time
  const expiresAt = new Date(Date.now() + expires_in * 1000);

  // Store connection (upsert to handle reconnections)
  await OAuthConnection.findOneAndUpdate(
    { userId: oauthState.userId, provider },
    {
      accessToken: access_token,
      refreshToken: refresh_token,
      expiresAt,
      scope: scope.split(" "),
    },
    { upsert: true, new: true },
  );

  // Clean up state
  await OAuthState.deleteOne({ _id: oauthState._id });

  return {
    success: true,
    provider,
    expiresAt,
  };
};
```

## Step 6: Token Refresh

### Background Job

**src/infrastructure/jobs/oauthTokenRefresh.js**:

```javascript
const cron = require("node-cron");
const OAuthConnection = require("../database/mongodb/models/OAuthConnection");
const refreshToken = require("../../application/useCases/oauth/refreshToken");
const logger = require("../logging/logger");

// Run every 5 minutes
const CRON_SCHEDULE = "*/5 * * * *";

function startTokenRefreshJob() {
  cron.schedule(CRON_SCHEDULE, async () => {
    try {
      logger.info("Starting OAuth token refresh job");

      // Find tokens expiring in next 10 minutes
      const expiringConnections = await OAuthConnection.find({
        expiresAt: {
          $lt: new Date(Date.now() + 10 * 60 * 1000),
        },
      });

      logger.info(`Found ${expiringConnections.length} tokens to refresh`);

      for (const connection of expiringConnections) {
        try {
          await refreshToken({
            userId: connection.userId,
            provider: connection.provider,
          });

          logger.info(
            `Refreshed token for user ${connection.userId}, provider ${connection.provider}`,
          );
        } catch (error) {
          logger.error(
            `Failed to refresh token for user ${connection.userId}:`,
            error,
          );
        }
      }

      logger.info("OAuth token refresh job completed");
    } catch (error) {
      logger.error("OAuth token refresh job failed:", error);
    }
  });

  logger.info(`OAuth token refresh job scheduled: ${CRON_SCHEDULE}`);
}

module.exports = { startTokenRefreshJob };
```

### Refresh Use Case

**src/application/useCases/oauth/refreshToken.js**:

```javascript
const axios = require("axios");
const OAuthConnection = require("../../../infrastructure/database/mongodb/models/OAuthConnection");
const config = require("../../../infrastructure/config");

module.exports = async function refreshToken({ userId, provider }) {
  const connection = await OAuthConnection.findOne({ userId, provider });

  if (!connection) {
    throw new Error("OAuth connection not found");
  }

  const { refreshToken } = connection.getDecryptedTokens();
  const providerConfig = config.oauth[provider];

  // Request new access token
  const tokenResponse = await axios.post(
    providerConfig.tokenEndpoint,
    {
      grant_type: "refresh_token",
      refresh_token: refreshToken,
      client_id: providerConfig.clientId,
      client_secret: providerConfig.clientSecret,
    },
    {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    },
  );

  const { access_token, expires_in } = tokenResponse.data;

  // Update connection
  connection.accessToken = access_token;
  connection.expiresAt = new Date(Date.now() + expires_in * 1000);
  await connection.save();

  return {
    success: true,
    expiresAt: connection.expiresAt,
  };
};
```

## Step 7: API Proxy Endpoints

Create proxy endpoints to make OAuth-authenticated requests on behalf of users.

**src/interfaces/http/controllers/klaviyoController.js**:

```javascript
const axios = require("axios");
const OAuthConnection = require("../../../infrastructure/database/mongodb/models/OAuthConnection");

exports.proxyRequest = async (req, res, next) => {
  try {
    const userId = req.user.id;
    const { method, endpoint } = req.body;
    const data = req.body.data || {};

    // Get user's OAuth connection
    const connection = await OAuthConnection.findOne({
      userId,
      provider: "klaviyo",
    });

    if (!connection) {
      return res.status(401).json({
        success: false,
        error: "Klaviyo not connected",
      });
    }

    const { accessToken } = connection.getDecryptedTokens();

    // Make request to Klaviyo API
    const response = await axios({
      method,
      url: `https://a.klaviyo.com/api${endpoint}`,
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
        revision: "2024-10-15",
      },
      data: method !== "GET" ? data : undefined,
      params: method === "GET" ? data : undefined,
    });

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error) {
    if (error.response?.status === 401) {
      // Token expired, trigger refresh
      // (Background job will handle this, return error for now)
      return res.status(401).json({
        success: false,
        error: "Token expired, please reconnect",
      });
    }

    next(error);
  }
};
```

## Testing OAuth Integration

**tests/oauth.test.js**:

```javascript
const request = require("supertest");
const app = require("../src/interfaces/http/server");
const OAuthState = require("../src/infrastructure/database/mongodb/models/OAuthState");

describe("OAuth Integration", () => {
  let authToken;
  let userId;

  beforeEach(async () => {
    // Setup: Create test user and get auth token
    // (Implementation depends on your auth system)
  });

  describe("POST /api/v1/oauth/:provider/initiate", () => {
    it("should generate authorization URL with PKCE", async () => {
      const response = await request(app)
        .post("/api/v1/oauth/klaviyo/initiate")
        .set("Authorization", `Bearer ${authToken}`)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.authorizationUrl).toContain("code_challenge");
      expect(response.body.data.state).toBeDefined();

      // Verify state stored in database
      const state = await OAuthState.findOne({
        state: response.body.data.state,
      });
      expect(state).toBeDefined();
      expect(state.codeVerifier).toBeDefined();
    });
  });
});
```

## Best Practices

1. **Always use PKCE** for OAuth flows (prevents authorization code interception)
2. **Encrypt tokens** at rest with AES-256
3. **Set token expiration** indexes for auto-cleanup
4. **Handle token refresh** proactively via background job
5. **Validate state parameter** to prevent CSRF attacks
6. **Use environment variables** for all credentials
7. **Log OAuth operations** for debugging and audit trails
8. **Implement retry logic** for token refresh failures
9. **Use unique compound indexes** (userId + provider) to prevent duplicates
10. **Test with multiple providers** to ensure abstraction works

## Next Steps

- See `reference/providers.md` for provider-specific OAuth configurations
- Check `reference/security.md` for additional security considerations
- Review `reference/troubleshooting-oauth.md` for common OAuth issues
