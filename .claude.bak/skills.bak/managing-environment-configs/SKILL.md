---
name: managing-environment-configs
description: Manage environment configuration across Native App (Python), Backend (Node.js), and Frontend (React/Vite). Covers .env files, validation, defaults, type safety, and environment-specific settings. Use when adding configuration options or debugging config issues.
---

# Managing Environment Configs

Manage environment configuration across all three Beena projects following each platform's best practices. Covers Python ConfigManager, Node.js dotenv, and Vite environment variables.

## When to Use This Skill

- Adding new configuration options to any project
- Setting up environment-specific configurations (dev/staging/prod)
- Implementing configuration validation
- Debugging configuration loading issues
- Managing secrets and sensitive data
- Creating default values and fallbacks
- Adding type-safe configuration access

## Native App (Python) - ConfigManager Pattern

### Configuration Manager

Located at `config/config_manager.py`:

```python
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

# Default configuration values
DEFAULT_CONFIG = {
    # API settings
    "API_PORT": 8000,
    "API_HOST": "127.0.0.1",

    # Chrome settings
    "CHROME_DEBUGGING_PORT": 9222,
    "CHROME_PATH": "",

    # Logging settings
    "LOG_LEVEL": "INFO",
    "LOG_FILE": "/tmp/beenanativeapp.log",
    "JSON_LOGGING": False,

    # Application settings
    "APP_NAME": "Beena",
    "APP_VERSION": "0.1.0",
    "ENVIRONMENT": "development",

    # Timeouts (in seconds)
    "CHROME_STARTUP_TIMEOUT": 30,
    "PLAYWRIGHT_TIMEOUT": 60,

    # Payment validation settings
    "BACKEND_API_URL": "http://localhost:5001",
    "PAYMENT_VALIDATION_ENABLED": True,
    "PAYMENT_CACHE_TTL_MINUTES": 30,
}

# Configuration validation rules
CONFIG_VALIDATION = {
    "API_PORT": lambda x: 1024 <= int(x) <= 65535,
    "CHROME_DEBUGGING_PORT": lambda x: 1024 <= int(x) <= 65535,
    "LOG_LEVEL": lambda x: x in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
    "ENVIRONMENT": lambda x: x in ("development", "testing", "production"),
}

class ConfigManager:
    """Configuration manager for the application."""

    def __init__(self, env_prefix: str = "", env_file: Optional[Union[str, Path]] = ".env"):
        """
        Initialize the configuration manager.

        Args:
            env_prefix: Prefix for environment variables (e.g., "BEENA_")
            env_file: Path to .env file to load variables from
        """
        self._config = DEFAULT_CONFIG.copy()
        self._env_prefix = env_prefix
        self._env_file = env_file

        # Load configuration from environment
        self._load_from_env()

    def _load_from_env(self):
        """Load configuration from environment variables and .env file."""
        # Load from .env file if it exists
        if self._env_file:
            env_path = Path(self._env_file)
            if env_path.exists():
                self._load_env_file(env_path)

        # Override with environment variables
        for key in self._config.keys():
            env_key = f"{self._env_prefix}{key}"
            if env_key in os.environ:
                value = os.environ[env_key]
                # Type coercion
                self._config[key] = self._coerce_type(key, value)

    def _load_env_file(self, env_path: Path):
        """Load variables from .env file."""
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")

                    # Remove prefix if present
                    if self._env_prefix and key.startswith(self._env_prefix):
                        key = key[len(self._env_prefix):]

                    if key in self._config:
                        self._config[key] = self._coerce_type(key, value)

    def _coerce_type(self, key: str, value: str) -> Any:
        """Coerce string value to appropriate type."""
        default_value = DEFAULT_CONFIG.get(key)

        if isinstance(default_value, bool):
            return value.lower() in ("true", "1", "yes")
        elif isinstance(default_value, int):
            return int(value)
        elif isinstance(default_value, float):
            return float(value)
        else:
            return value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        value = self._config.get(key, default)

        # Validate if validator exists
        if key in CONFIG_VALIDATION:
            validator = CONFIG_VALIDATION[key]
            if not validator(value):
                raise ValueError(f"Invalid value for {key}: {value}")

        return value

    def set(self, key: str, value: Any):
        """Set a configuration value (runtime only)."""
        self._config[key] = value

# Global config instance
config = ConfigManager()
```

### Usage in Native App

```python
# Import global config
from beenanativeapp.config.config_manager import config

# Get configuration values
api_port = config.get("API_PORT", 8000)
log_level = config.get("LOG_LEVEL", "INFO")
backend_url = config.get("BACKEND_API_URL")

# Use in FastAPI
@app.on_event("startup")
async def startup():
    logger.info(f"Starting {config.get('APP_NAME')} v{config.get('APP_VERSION')}")
    logger.info(f"Environment: {config.get('ENVIRONMENT')}")
```

### .env File Format (Native App)

```env
# .env
API_PORT=8000
API_HOST=127.0.0.1
LOG_LEVEL=DEBUG
ENVIRONMENT=development

# Payment settings
BACKEND_API_URL=http://localhost:5001
PAYMENT_VALIDATION_ENABLED=true
PAYMENT_CACHE_TTL_MINUTES=30

# Playwright settings
PLAYWRIGHT_TIMEOUT=120
CHROME_STARTUP_TIMEOUT=45
```

## Backend (Node.js) - dotenv Pattern

### Configuration Module

Located at `src/config/index.js`:

```javascript
require("dotenv").config();

module.exports = {
  // Server settings
  port: process.env.PORT || 3001,
  host: process.env.HOST || "localhost",
  nodeEnv: process.env.NODE_ENV || "development",

  // Database settings
  mongodb: {
    uri: process.env.MONGODB_URI || "mongodb://localhost:27017/beena",
    options: {
      useNewUrlParser: true,
      useUnifiedTopology: true,
    },
  },

  // JWT settings
  jwt: {
    secret: process.env.JWT_SECRET || "your-secret-key",
    expiresIn: process.env.JWT_EXPIRES_IN || "24h",
    refreshSecret: process.env.JWT_REFRESH_SECRET || "your-refresh-secret",
    refreshExpiresIn: process.env.JWT_REFRESH_EXPIRES_IN || "7d",
  },

  // OAuth settings
  klaviyo: {
    clientId: process.env.KLAVIYO_CLIENT_ID,
    clientSecret: process.env.KLAVIYO_CLIENT_SECRET,
    redirectUri: process.env.KLAVIYO_REDIRECT_URI,
    scopes: ["lists:read", "lists:write", "campaigns:read", "campaigns:write"],
  },

  // Encryption
  encryption: {
    algorithm: "aes-256-gcm",
    key:
      process.env.ENCRYPTION_KEY ||
      Buffer.from("your-32-byte-key-here", "utf8"),
  },

  // Stripe
  stripe: {
    secretKey: process.env.STRIPE_SECRET_KEY,
    publishableKey: process.env.STRIPE_PUBLISHABLE_KEY,
    webhookSecret: process.env.STRIPE_WEBHOOK_SECRET,
  },

  // CORS
  cors: {
    origin: process.env.CORS_ORIGIN || "http://localhost:3000",
    credentials: true,
  },

  // Logging
  logging: {
    level: process.env.LOG_LEVEL || "info",
    file: process.env.LOG_FILE || "logs/app.log",
  },
};
```

### Type-Safe Config (TypeScript)

```typescript
// src/config/index.ts
import dotenv from "dotenv";

dotenv.config();

interface Config {
  port: number;
  host: string;
  nodeEnv: "development" | "production" | "test";
  mongodb: {
    uri: string;
    options: Record<string, any>;
  };
  jwt: {
    secret: string;
    expiresIn: string;
    refreshSecret: string;
    refreshExpiresIn: string;
  };
}

const config: Config = {
  port: parseInt(process.env.PORT || "3001", 10),
  host: process.env.HOST || "localhost",
  nodeEnv: (process.env.NODE_ENV as Config["nodeEnv"]) || "development",

  mongodb: {
    uri: process.env.MONGODB_URI || "mongodb://localhost:27017/beena",
    options: {
      useNewUrlParser: true,
      useUnifiedTopology: true,
    },
  },

  jwt: {
    secret: process.env.JWT_SECRET || "your-secret-key",
    expiresIn: process.env.JWT_EXPIRES_IN || "24h",
    refreshSecret: process.env.JWT_REFRESH_SECRET || "your-refresh-secret",
    refreshExpiresIn: process.env.JWT_REFRESH_EXPIRES_IN || "7d",
  },
};

export default config;
```

### Usage in Backend

```javascript
const config = require("../config");

// Use in Express
app.listen(config.port, config.host, () => {
  console.log(`Server running on ${config.host}:${config.port}`);
  console.log(`Environment: ${config.nodeEnv}`);
});

// Use in services
const mongoose = require("mongoose");
mongoose.connect(config.mongodb.uri, config.mongodb.options);

// Use in middleware
const jwt = require("jsonwebtoken");
const token = jwt.sign(payload, config.jwt.secret, {
  expiresIn: config.jwt.expiresIn,
});
```

### .env File Format (Backend)

```env
# .env
NODE_ENV=development
PORT=3001
HOST=localhost

# Database
MONGODB_URI=mongodb://localhost:27017/beena

# JWT
JWT_SECRET=your-super-secret-jwt-key-change-in-production
JWT_EXPIRES_IN=24h
JWT_REFRESH_SECRET=your-super-secret-refresh-key
JWT_REFRESH_EXPIRES_IN=7d

# OAuth - Klaviyo
KLAVIYO_CLIENT_ID=your-klaviyo-client-id
KLAVIYO_CLIENT_SECRET=your-klaviyo-client-secret
KLAVIYO_REDIRECT_URI=http://localhost:3001/api/v1/oauth/klaviyo/callback

# Encryption
ENCRYPTION_KEY=your-32-character-encryption-key-here

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# CORS
CORS_ORIGIN=http://localhost:3000

# Logging
LOG_LEVEL=debug
LOG_FILE=logs/app.log
```

## Frontend (React/Vite) - import.meta.env Pattern

### Environment Variables

Vite automatically loads env variables from `.env` files with the `VITE_` prefix:

```typescript
// src/config/index.ts
interface Config {
  apiUrl: string;
  stripePublishableKey: string;
  environment: string;
  enableAnalytics: boolean;
}

const config: Config = {
  apiUrl: import.meta.env.VITE_API_URL || "http://localhost:3001",
  stripePublishableKey: import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || "",
  environment: import.meta.env.MODE || "development",
  enableAnalytics: import.meta.env.VITE_ENABLE_ANALYTICS === "true",
};

export default config;
```

### Usage in Frontend

```typescript
import config from "@/config";

// API calls
const response = await fetch(`${config.apiUrl}/api/v1/users`);

// Stripe
import { loadStripe } from "@stripe/stripe-js";
const stripe = await loadStripe(config.stripePublishableKey);

// Conditional features
if (config.enableAnalytics) {
  trackEvent("page_view", { page: "/dashboard" });
}

// Environment checks
if (config.environment === "production") {
  console.log = () => {}; // Disable logging in production
}
```

### .env Files (Frontend)

```env
# .env.development
VITE_API_URL=http://localhost:3001
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_...
VITE_ENABLE_ANALYTICS=false

# .env.production
VITE_API_URL=https://api.beena.com
VITE_STRIPE_PUBLISHABLE_KEY=pk_live_...
VITE_ENABLE_ANALYTICS=true

# .env.local (gitignored, for local overrides)
VITE_API_URL=http://192.168.1.100:3001
```

### TypeScript Environment Types

```typescript
// src/vite-env.d.ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_STRIPE_PUBLISHABLE_KEY: string;
  readonly VITE_ENABLE_ANALYTICS: string;
  // Add more as needed
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
```

## Configuration Validation

### Python Validation

```python
# config/validators.py
def validate_port(port: int) -> bool:
    """Validate port number."""
    return 1024 <= port <= 65535

def validate_url(url: str) -> bool:
    """Validate URL format."""
    return url.startswith(('http://', 'https://'))

def validate_log_level(level: str) -> bool:
    """Validate log level."""
    return level in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')

CONFIG_VALIDATION = {
    'API_PORT': validate_port,
    'BACKEND_API_URL': validate_url,
    'LOG_LEVEL': validate_log_level,
}
```

### Node.js Validation

```javascript
// config/validators.js
const Joi = require("joi");

const configSchema = Joi.object({
  port: Joi.number().integer().min(1024).max(65535).required(),
  host: Joi.string().hostname().required(),
  nodeEnv: Joi.string().valid("development", "production", "test").required(),
  mongodb: Joi.object({
    uri: Joi.string().uri().required(),
  }).required(),
  jwt: Joi.object({
    secret: Joi.string().min(32).required(),
    expiresIn: Joi.string().required(),
  }).required(),
});

const { error, value } = configSchema.validate(config);
if (error) {
  throw new Error(`Config validation error: ${error.message}`);
}

module.exports = value;
```

## Environment-Specific Configuration

### Multiple .env Files

```bash
# Development
.env.development

# Testing
.env.test

# Production
.env.production

# Local overrides (gitignored)
.env.local
```

### Loading Priority (Vite)

```
.env.local          # Highest priority (gitignored)
.env.[mode].local   # Mode-specific, gitignored
.env.[mode]         # Mode-specific
.env                # Base configuration
```

### Dynamic Loading (Node.js)

```javascript
const dotenv = require("dotenv");
const path = require("path");

const env = process.env.NODE_ENV || "development";
const envFile = path.resolve(__dirname, `../.env.${env}`);

// Load environment-specific file
dotenv.config({ path: envFile });

// Fallback to default .env
dotenv.config();
```

## Secrets Management

### DO NOT commit secrets

```.gitignore
# Environment files with secrets
.env.local
.env.production
.env.*.local

# Encryption keys
*.key
*.pem
```

### Use Environment Variables in CI/CD

```yaml
# GitHub Actions
env:
  MONGODB_URI: ${{ secrets.MONGODB_URI }}
  JWT_SECRET: ${{ secrets.JWT_SECRET }}
  STRIPE_SECRET_KEY: ${{ secrets.STRIPE_SECRET_KEY }}
```

### Encrypt Sensitive Config

```python
# Python encryption
from cryptography.fernet import Fernet

def encrypt_config_value(value: str, key: bytes) -> str:
    """Encrypt a configuration value."""
    f = Fernet(key)
    return f.encrypt(value.encode()).decode()

def decrypt_config_value(encrypted: str, key: bytes) -> str:
    """Decrypt a configuration value."""
    f = Fernet(key)
    return f.decrypt(encrypted.encode()).decode()

# Store encrypted in .env
ENCRYPTED_API_KEY=gAAAAABh...encrypted-value...
```

## Best Practices

1. **Use environment-specific files** (.env.development, .env.production)
2. **Provide sensible defaults** for all non-sensitive config
3. **Validate configuration** on application startup
4. **Never commit secrets** - use .gitignore and secret management
5. **Use type-safe config access** (TypeScript interfaces, dataclasses)
6. **Prefix frontend env vars** with VITE\_ for security
7. **Document all config options** in comments or README
8. **Use consistent naming** across all projects
9. **Fail fast on missing required config** - don't use empty defaults for secrets
10. **Log config on startup** (but redact secrets)

## Common Pitfalls

❌ **Committing .env files with secrets**

```bash
# BAD: .env in git
git add .env
```

✅ **Gitignore sensitive env files**

```bash
# GOOD: .gitignore
.env.local
.env.production
```

❌ **No validation on startup**

```javascript
// BAD: Missing config causes runtime errors
const apiKey = process.env.API_KEY;
// Later... undefined error
```

✅ **Validate on startup**

```javascript
// GOOD: Fail fast with clear error
if (!process.env.API_KEY) {
  throw new Error("API_KEY environment variable is required");
}
```

❌ **Exposing secrets in frontend**

```typescript
// BAD: Secret exposed to client
const SECRET_KEY = import.meta.env.VITE_SECRET_KEY;
```

✅ **Keep secrets in backend**

```typescript
// GOOD: Only non-sensitive config in frontend
const API_URL = import.meta.env.VITE_API_URL; // OK - not secret
// Secret key stays in backend only
```

## Example: Adding New Config Option

### 1. Add to Native App

```python
# config/config_manager.py
DEFAULT_CONFIG = {
    # ... existing config
    "MAX_CONCURRENT_JOBS": 3,  # Add new option
}

CONFIG_VALIDATION = {
    # ... existing validation
    "MAX_CONCURRENT_JOBS": lambda x: 1 <= int(x) <= 10,
}
```

### 2. Add to Backend

```javascript
// config/index.js
module.exports = {
  // ... existing config
  jobs: {
    maxConcurrent: parseInt(process.env.MAX_CONCURRENT_JOBS) || 3,
  },
};
```

### 3. Add to Frontend (if needed)

```typescript
// src/config/index.ts
const config = {
  // ... existing config
  maxConcurrentJobs: parseInt(
    import.meta.env.VITE_MAX_CONCURRENT_JOBS || "3",
    10,
  ),
};
```

### 4. Update .env Files

```env
# Native App .env
MAX_CONCURRENT_JOBS=5

# Backend .env
MAX_CONCURRENT_JOBS=5

# Frontend .env
VITE_MAX_CONCURRENT_JOBS=5
```

### 5. Document the Option

```markdown
# Configuration Options

## MAX_CONCURRENT_JOBS

- **Type**: Integer
- **Default**: 3
- **Range**: 1-10
- **Description**: Maximum number of jobs that can run concurrently in the worker
```

## Next Steps

- See project-specific README files for complete configuration documentation
- Review `.env.example` files for all available options
- Check CI/CD configuration for production environment setup
- See `reference/secrets-management.md` for advanced secret handling
