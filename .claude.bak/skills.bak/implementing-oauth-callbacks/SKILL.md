---
name: implementing-oauth-callbacks
description: Handle OAuth callback pages in the React frontend for ESP integrations like Klaviyo. Covers URL parameter extraction, error handling, backend delegation, loading states, and connection status. Use when adding new OAuth integrations or fixing callback flows.
---

# Implementing OAuth Callbacks

Handle OAuth 2.0 callback flows in the Beena frontend for third-party ESP integrations. Focuses on the project's pattern of delegating token exchange to the backend while providing excellent user experience.

## When to Use This Skill

- Adding new OAuth integration (Klaviyo, Mailchimp, Yotpo, etc.)
- Implementing OAuth callback page for authorization code flow
- Creating error handling pages for OAuth failures
- Building installation/connection pages for ESP integrations
- Debugging OAuth callback issues
- Adding connection status checking
- Implementing retry logic for failed connections

## OAuth Flow Architecture

### Three-Page Pattern

The project uses a three-page pattern for OAuth flows:

1. **Install Page** (`/integrations/{provider}/install`)
   - Initiates OAuth flow
   - Checks user authentication
   - Calls backend to get authorization URL
   - Redirects to provider

2. **Callback Page** (`/integrations/{provider}/callback`)
   - Receives OAuth response from provider
   - Validates parameters (code, state, error)
   - Delegates token exchange to backend
   - Shows loading state

3. **Error Page** (`/integrations/{provider}/error`)
   - Handles OAuth errors with user-friendly messages
   - Provides retry and troubleshooting options
   - Shows contextual help based on error type

### Backend Delegation Pattern

**Important:** The frontend does NOT exchange tokens. It receives the callback, validates parameters, and redirects to the backend:

```
User → Provider OAuth → Frontend Callback → Backend Token Exchange → Success/Error Page
```

## Install Page Pattern

Located at: `src/pages/integrations/{provider}/install.tsx`

### Complete Install Page

```tsx
import React, { useEffect, useState } from "react";
import { Card, Typography, Spin, Alert, Button, Space } from "antd";
import { LoadingOutlined, RocketOutlined } from "@ant-design/icons";
import { useNavigate, useSearchParams } from "react-router-dom";
import styled from "styled-components";
import { useAuth } from "../../../hooks/useAuth";
import { API } from "../../../shared/utils/api";

const { Title, Text } = Typography;

const PageContainer = styled.div`
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
`;

const InstallCard = styled(Card)`
  max-width: 600px;
  width: 100%;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  text-align: center;
`;

const ProcessingContainer = styled.div`
  padding: 40px 20px;
`;

const KlaviyoInstallPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isAuthenticated, authContextLoading: authLoading } = useAuth();
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const source = searchParams.get("source");
  const isFromProvider =
    source === "klaviyo" || source === "klaviyo_marketplace";

  const initiateOAuth = async () => {
    try {
      setProcessing(true);
      setError(null);

      // Call backend to initiate OAuth flow
      const response = await API.post("/oauth/klaviyo/connect", {
        installSource: isFromProvider ? "klaviyo_marketplace" : "app",
        returnUrl: window.location.origin + "/integrations/klaviyo/callback",
      });

      if (response.data.success && response.data.authorizationUrl) {
        // Redirect to provider OAuth authorization page
        window.location.href = response.data.authorizationUrl;
      } else {
        throw new Error("Failed to get authorization URL");
      }
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.error || "Failed to start installation process";
      setError(errorMessage);
      setProcessing(false);
    }
  };

  useEffect(() => {
    if (!authLoading) {
      if (isAuthenticated()) {
        // User is authenticated, proceed with OAuth
        initiateOAuth();
      } else {
        // User needs to login first - store return URL
        const returnUrl = window.location.href;
        window.sessionStorage.setItem("oauth_return_url", returnUrl);
        navigate(
          `/login?return=${encodeURIComponent("/integrations/klaviyo/install")}${source ? `&source=${source}` : ""}`,
        );
      }
    }
  }, [authLoading, navigate, source]);

  const handleRetry = () => {
    setError(null);
    initiateOAuth();
  };

  const handleCancel = () => {
    navigate("/integrations");
  };

  if (authLoading || processing) {
    return (
      <PageContainer>
        <InstallCard>
          <ProcessingContainer>
            <Spin
              indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />}
              tip={
                authLoading
                  ? "Checking authentication status..."
                  : "Preparing Klaviyo connection..."
              }
            />
            <Title level={3} style={{ marginTop: 24 }}>
              {isFromProvider
                ? "Installing from Klaviyo..."
                : "Connecting to Klaviyo..."}
            </Title>
            <Text type="secondary">
              Please wait while we prepare your connection. You'll be redirected
              to Klaviyo shortly.
            </Text>
          </ProcessingContainer>
        </InstallCard>
      </PageContainer>
    );
  }

  if (error) {
    return (
      <PageContainer>
        <InstallCard>
          <Alert
            message="Installation Failed"
            description={error}
            type="error"
            showIcon
            style={{ marginBottom: 24 }}
          />
          <Space>
            <Button type="primary" onClick={handleRetry}>
              Try Again
            </Button>
            <Button onClick={handleCancel}>Cancel</Button>
          </Space>
        </InstallCard>
      </PageContainer>
    );
  }

  return null; // Will redirect before showing anything
};

export default KlaviyoInstallPage;
```

### Key Patterns

**1. Authentication Gating**

```tsx
useEffect(() => {
  if (!authLoading) {
    if (isAuthenticated()) {
      // Proceed with OAuth
      initiateOAuth();
    } else {
      // Redirect to login with return URL
      window.sessionStorage.setItem("oauth_return_url", window.location.href);
      navigate(`/login?return=${encodeURIComponent(currentPath)}`);
    }
  }
}, [authLoading]);
```

**2. Backend OAuth Initiation**

```tsx
const response = await API.post("/oauth/{provider}/connect", {
  installSource: "app", // or 'provider_marketplace'
  returnUrl: window.location.origin + "/integrations/{provider}/callback",
});

if (response.data.success && response.data.authorizationUrl) {
  // Full page redirect to provider
  window.location.href = response.data.authorizationUrl;
}
```

**Important:**

- Use `window.location.href` for full page redirect (not React Router navigate)
- Backend returns pre-built authorization URL with all parameters
- Frontend does NOT build OAuth URLs - backend handles state, PKCE, etc.

**3. Source Detection**

```tsx
const source = searchParams.get("source");
const isFromProvider = source === "klaviyo" || source === "klaviyo_marketplace";

// Customize UI based on source
<Title>
  {isFromProvider ? "Installing from Klaviyo..." : "Connecting to Klaviyo..."}
</Title>;
```

## Callback Page Pattern

Located at: `src/pages/integrations/{provider}/callback.tsx`

### Complete Callback Page

```tsx
import React, { useEffect, useState } from "react";
import { Card, Spin, Alert, Typography } from "antd";
import { LoadingOutlined } from "@ant-design/icons";
import { useNavigate, useSearchParams } from "react-router-dom";
import styled from "styled-components";

const { Title, Text } = Typography;

const PageContainer = styled.div`
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
`;

const CallbackCard = styled(Card)`
  max-width: 500px;
  width: 100%;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  text-align: center;
`;

const ProcessingContainer = styled.div`
  padding: 40px 20px;
`;

const KlaviyoCallbackPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get("code");
      const state = searchParams.get("state");
      const errorParam = searchParams.get("error");
      const errorDescription = searchParams.get("error_description");

      // Handle OAuth errors from provider
      if (errorParam) {
        if (errorParam === "access_denied") {
          navigate("/integrations/klaviyo/error?reason=denied");
        } else {
          navigate("/integrations/klaviyo/error?reason=failed");
        }
        return;
      }

      // Validate required parameters
      if (!code || !state) {
        navigate("/integrations/klaviyo/error?reason=invalid_params");
        return;
      }

      try {
        // Delegate to backend for token exchange
        const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:3001";
        const backendCallbackUrl = `${apiUrl}/api/v1/oauth/klaviyo/callback?code=${code}&state=${state}`;

        // Redirect to backend to complete OAuth flow
        window.location.href = backendCallbackUrl;
      } catch (error: any) {
        setError("Failed to complete the connection process");

        // Redirect to error page after showing error briefly
        setTimeout(() => {
          navigate("/integrations/klaviyo/error?reason=exchange_failed");
        }, 2000);
      }
    };

    handleCallback();
  }, [navigate, searchParams]);

  if (error) {
    return (
      <PageContainer>
        <CallbackCard>
          <Alert
            message="Connection Error"
            description={error}
            type="error"
            showIcon
          />
        </CallbackCard>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <CallbackCard>
        <ProcessingContainer>
          <Spin
            indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />}
            tip="Completing connection..."
          />
          <Title level={3} style={{ marginTop: 24 }}>
            Almost there!
          </Title>
          <Text type="secondary">
            We're finalizing your Klaviyo connection. This should only take a
            moment...
          </Text>
        </ProcessingContainer>
      </CallbackCard>
    </PageContainer>
  );
};

export default KlaviyoCallbackPage;
```

### Key Patterns

**1. Parameter Extraction and Validation**

```tsx
const code = searchParams.get("code");
const state = searchParams.get("state");
const errorParam = searchParams.get("error");
const errorDescription = searchParams.get("error_description");

// Handle provider errors
if (errorParam) {
  if (errorParam === "access_denied") {
    navigate("/integrations/{provider}/error?reason=denied");
  } else {
    navigate("/integrations/{provider}/error?reason=failed");
  }
  return;
}

// Validate required parameters
if (!code || !state) {
  navigate("/integrations/{provider}/error?reason=invalid_params");
  return;
}
```

**2. Backend Delegation**

```tsx
// Build backend callback URL with query parameters
const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:3001";
const backendCallbackUrl = `${apiUrl}/api/v1/oauth/{provider}/callback?code=${code}&state=${state}`;

// Full page redirect to backend
window.location.href = backendCallbackUrl;
```

**Important:**

- Frontend receives callback from provider
- Frontend validates parameters only
- Backend handles token exchange, state validation, PKCE verification
- Backend redirects to success/error page after completion

**3. Error Handling with Delay**

```tsx
try {
  // ... redirect to backend
} catch (error: any) {
  setError("Failed to complete the connection process");

  // Show error briefly, then redirect
  setTimeout(() => {
    navigate("/integrations/{provider}/error?reason=exchange_failed");
  }, 2000);
}
```

## Error Page Pattern

Located at: `src/pages/integrations/{provider}/error.tsx`

### Error Reason Definitions

```tsx
interface ErrorInfo {
  title: string;
  description: string;
  icon?: React.ReactNode;
  showRetry?: boolean;
}

const errorReasons: Record<string, ErrorInfo> = {
  denied: {
    title: "Permission Denied",
    description:
      "You denied the permission request. To use this integration, you need to grant the necessary permissions to access your Klaviyo account.",
    icon: <WarningOutlined style={{ color: "#faad14" }} />,
    showRetry: true,
  },
  expired: {
    title: "Authorization Expired",
    description:
      "The authorization code has expired. Authorization codes are only valid for 5 minutes. Please try connecting again.",
    icon: <CloseCircleOutlined style={{ color: "#ff4d4f" }} />,
    showRetry: true,
  },
  invalid_params: {
    title: "Invalid Parameters",
    description:
      "The authorization request contained invalid parameters. Please try again or contact support if the issue persists.",
    showRetry: true,
  },
  exchange_failed: {
    title: "Connection Failed",
    description:
      "Failed to establish connection with Klaviyo. This might be a temporary issue. Please try again in a few moments.",
    showRetry: true,
  },
  no_pending: {
    title: "No Pending Connection",
    description:
      "There is no pending OAuth connection to complete. Please start the connection process from the integrations page.",
    showRetry: false,
  },
  failed: {
    title: "Connection Failed",
    description:
      "An unexpected error occurred while connecting to Klaviyo. Please try again or contact support if the issue persists.",
    showRetry: true,
  },
};
```

### Error Page Component

```tsx
const KlaviyoErrorPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const reason = searchParams.get("reason") || "failed";
  const errorInfo = errorReasons[reason] || errorReasons.failed;

  const handleRetry = () => {
    navigate("/integrations/klaviyo");
  };

  const handleGoToIntegrations = () => {
    navigate("/integrations");
  };

  return (
    <PageContainer>
      <ErrorCard>
        <Result
          status="error"
          icon={errorInfo.icon}
          title={<Title level={2}>{errorInfo.title}</Title>}
          subTitle={<Paragraph>{errorInfo.description}</Paragraph>}
          extra={[
            errorInfo.showRetry && (
              <Button type="primary" key="retry" onClick={handleRetry}>
                Try Again
              </Button>
            ),
            <Button key="integrations" onClick={handleGoToIntegrations}>
              Back to Integrations
            </Button>,
            <Button key="support" onClick={handleContactSupport} type="link">
              Contact Support
            </Button>,
          ].filter(Boolean)}
        />

        <ErrorDetails>
          <Title level={5}>What can you do?</Title>
          <Space direction="vertical">
            {errorInfo.showRetry && (
              <Text>
                🔄 Try connecting again by clicking the "Try Again" button
              </Text>
            )}
            <Text>📧 Contact our support team if the issue persists</Text>
            <Text>🔍 Check your Klaviyo account permissions and settings</Text>
            <Text>🌐 Ensure you have a stable internet connection</Text>
          </Space>
        </ErrorDetails>

        {reason === "expired" && (
          <Alert
            message="Quick Tip"
            description="Authorization codes expire after 5 minutes for security reasons. Make sure to complete the authorization process quickly after starting it."
            type="info"
            showIcon
            style={{ marginTop: 16 }}
          />
        )}

        {reason === "denied" && (
          <Alert
            message="Why do we need these permissions?"
            description="The requested permissions are necessary for the integration to function properly. We only request the minimum permissions needed to sync data and create automations."
            type="warning"
            showIcon
            style={{ marginTop: 16 }}
          />
        )}
      </ErrorCard>
    </PageContainer>
  );
};
```

## Connection Status Pattern

### Check Connection Status

```tsx
import { API } from "@/shared/utils/api";

const checkConnectionStatus = async () => {
  try {
    setLoading(true);
    const response = await API.get("/oauth/{provider}/status");
    setIsConnected(response.data.success && response.data.connected);
  } catch (error) {
    console.error("Failed to check connection status:", error);
    setIsConnected(false);
  } finally {
    setLoading(false);
  }
};

useEffect(() => {
  checkConnectionStatus();

  // Check if returning from OAuth callback
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("oauth_success") === "true") {
    // Clear the URL parameter
    window.history.replaceState({}, document.title, window.location.pathname);
    checkConnectionStatus();
  }
}, []);
```

**Pattern explanation:**

- Check connection status on mount
- Look for `oauth_success` URL parameter (set by backend redirect)
- Clear URL parameter after detecting it
- Recheck status to get latest connection info

### Connection Status UI

```tsx
{
  isConnected ? (
    <KlaviyoConnectionStatus
      onDisconnect={handleDisconnect}
      onReconnect={handleReconnect}
    />
  ) : (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <Alert
        message="Connect Your Klaviyo Account"
        description="Integrate with Klaviyo to unlock powerful marketing automation features."
        type="info"
        showIcon
      />
      <KlaviyoConnectButton onSuccess={handleConnectionSuccess} size="large" />
    </Space>
  );
}
```

## Environment Configuration

### API URL Configuration

```tsx
// Use environment variable with fallback
const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:3001";

// Build backend URLs
const connectUrl = `${apiUrl}/api/v1/oauth/{provider}/connect`;
const callbackUrl = `${apiUrl}/api/v1/oauth/{provider}/callback`;
const statusUrl = `${apiUrl}/api/v1/oauth/{provider}/status`;
```

**Environment variables:**

```env
# .env.development
VITE_API_URL=http://localhost:3001

# .env.production
VITE_API_URL=https://api.beena.com
```

## Routing Configuration

### Add Routes

```tsx
// src/App.tsx or router configuration
import KlaviyoInstallPage from "./pages/integrations/klaviyo/install";
import KlaviyoCallbackPage from "./pages/integrations/klaviyo/callback";
import KlaviyoErrorPage from "./pages/integrations/klaviyo/error";

<Routes>
  <Route
    path="/integrations/klaviyo/install"
    element={<KlaviyoInstallPage />}
  />
  <Route
    path="/integrations/klaviyo/callback"
    element={<KlaviyoCallbackPage />}
  />
  <Route path="/integrations/klaviyo/error" element={<KlaviyoErrorPage />} />
</Routes>;
```

## Styled Components Pattern

### Standard Styling

```tsx
import styled from "styled-components";

const PageContainer = styled.div`
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
`;

const Card = styled(AntCard)`
  max-width: 600px;
  width: 100%;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  text-align: center;
`;

const ProcessingContainer = styled.div`
  padding: 40px 20px;
`;
```

**Project standards:**

- Full-height gradient backgrounds for auth/OAuth pages
- Centered card layout with max-width constraint
- Box shadow for card depth
- Consistent padding and spacing

## Best Practices

1. **Always check authentication** before initiating OAuth
2. **Store return URLs** in sessionStorage for post-login redirect
3. **Validate all callback parameters** (code, state, error)
4. **Delegate token exchange to backend** - never handle tokens in frontend
5. **Use full page redirects** (`window.location.href`) for OAuth, not React Router
6. **Provide user-friendly error messages** with actionable steps
7. **Show loading states** during all async operations
8. **Clear URL parameters** after processing OAuth success flag
9. **Use environment variables** for API URLs with fallbacks
10. **Handle all OAuth error scenarios** (denied, expired, invalid, failed)

## Common Pitfalls

❌ **Handling token exchange in frontend**

```tsx
// BAD: Frontend should never receive or handle access tokens
const response = await fetch(`https://provider.com/token`, {
  method: "POST",
  body: JSON.stringify({ code, client_secret }),
});
const { access_token } = await response.json();
```

✅ **Delegate to backend**

```tsx
// GOOD: Redirect to backend with authorization code
window.location.href = `${apiUrl}/oauth/{provider}/callback?code=${code}&state=${state}`;
```

❌ **Using React Router navigate for OAuth redirects**

```tsx
// BAD: React Router can't navigate to external URLs
navigate("https://provider.com/oauth/authorize");
```

✅ **Use window.location.href**

```tsx
// GOOD: Full page redirect to provider
window.location.href = response.data.authorizationUrl;
```

❌ **Not validating callback parameters**

```tsx
// BAD: Blindly using parameters
const code = searchParams.get("code");
redirectToBackend(code); // Could be null/undefined
```

✅ **Validate before use**

```tsx
// GOOD: Validate and handle missing parameters
if (!code || !state) {
  navigate("/error?reason=invalid_params");
  return;
}
```

## Integration Example

Complete example for adding a new provider:

1. **Create install page** at `src/pages/integrations/mailchimp/install.tsx`
2. **Create callback page** at `src/pages/integrations/mailchimp/callback.tsx`
3. **Create error page** at `src/pages/integrations/mailchimp/error.tsx`
4. **Add routes** in `src/App.tsx`
5. **Update backend** to add `/oauth/mailchimp/*` endpoints
6. **Test flow:**
   - Visit install page → redirects to Mailchimp
   - Approve in Mailchimp → redirects to callback page
   - Callback validates → redirects to backend
   - Backend exchanges token → redirects to success page

## Security Considerations

1. **Never log sensitive data** (codes, tokens, state values)
2. **Use HTTPS** in production for all OAuth redirects
3. **Validate state parameter** on backend to prevent CSRF
4. **Set short expiration** on authorization codes (5 minutes)
5. **Store tokens encrypted** in backend database
6. **Use PKCE** for mobile/SPA OAuth flows (backend handles)
7. **Don't expose client secrets** in frontend code

## Next Steps

- See `reference/oauth-flow-diagram.md` for visual flow representation
- Check backend `implementing-oauth-flows` skill for token exchange patterns
- Review `reference/provider-specific-quirks.md` for ESP-specific OAuth details
