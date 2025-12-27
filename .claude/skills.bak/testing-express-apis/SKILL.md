---
name: testing-express-apis
description: Test Express.js APIs in the Beena backend. Covers unit tests, integration tests, mocking, test data, CI/CD integration, and coverage reporting. Use when writing tests for new endpoints or debugging test failures.
---

# Testing Express APIs

Implement comprehensive testing for Express.js APIs in the Beena backend following Jest/Supertest patterns with Clean Architecture principles.

## When to Use This Skill

- Writing tests for new API endpoints
- Adding integration tests for OAuth flows
- Mocking external dependencies (Stripe, Klaviyo, Mailchimp)
- Testing authentication and authorization
- Setting up test database and fixtures
- Debugging failing tests in CI/CD
- Improving test coverage
- Testing error scenarios

## Test Stack

### Testing Tools

```json
// package.json dependencies
{
  "devDependencies": {
    "jest": "^29.5.0",
    "supertest": "^6.3.3",
    "@types/jest": "^29.5.0",
    "@types/supertest": "^2.0.12",
    "mongodb-memory-server": "^8.12.2",
    "nock": "^13.3.0"
  }
}
```

### Jest Configuration

```javascript
// jest.config.js
module.exports = {
  testEnvironment: "node",
  roots: ["<rootDir>/src"],
  testMatch: ["**/__tests__/**/*.test.js", "**/?(*.)+(spec|test).js"],
  coverageDirectory: "coverage",
  coveragePathIgnorePatterns: ["/node_modules/", "/dist/"],
  collectCoverageFrom: ["src/**/*.{js,ts}", "!src/**/*.d.ts", "!src/index.js"],
  setupFilesAfterEnv: ["<rootDir>/src/tests/setup.js"],
  testTimeout: 10000,
  verbose: true,
};
```

## Test Structure

### Organizing Tests

```
src/
├── tests/
│   ├── setup.js                    # Global test setup
│   ├── teardown.js                 # Global teardown
│   ├── helpers/
│   │   ├── testDatabase.js        # Test DB utilities
│   │   ├── factories.js           # Test data factories
│   │   └── mocks.js               # Mock implementations
│   ├── unit/
│   │   ├── services/
│   │   │   ├── auth.test.js
│   │   │   └── oauth.test.js
│   │   └── utils/
│   │       └── encryption.test.js
│   └── integration/
│       ├── auth.test.js
│       ├── oauth.test.js
│       └── workflows.test.js
```

## Test Setup

### Global Setup

```javascript
// tests/setup.js
const { MongoMemoryServer } = require("mongodb-memory-server");
const mongoose = require("mongoose");

let mongoServer;

beforeAll(async () => {
  // Start in-memory MongoDB
  mongoServer = await MongoMemoryServer.create();
  const mongoUri = mongoServer.getUri();

  await mongoose.connect(mongoUri, {
    useNewUrlParser: true,
    useUnifiedTopology: true,
  });

  console.log("Test database connected");
});

afterAll(async () => {
  // Cleanup
  await mongoose.disconnect();
  await mongoServer.stop();
  console.log("Test database disconnected");
});

afterEach(async () => {
  // Clear all collections after each test
  const collections = mongoose.connection.collections;
  for (const key in collections) {
    await collections[key].deleteMany({});
  }
});
```

### Test Database Utilities

```javascript
// tests/helpers/testDatabase.js
const mongoose = require("mongoose");

class TestDatabase {
  static async clearCollection(collectionName) {
    const collection = mongoose.connection.collections[collectionName];
    if (collection) {
      await collection.deleteMany({});
    }
  }

  static async clearAllCollections() {
    const collections = mongoose.connection.collections;
    for (const key in collections) {
      await collections[key].deleteMany({});
    }
  }

  static async seedCollection(collectionName, documents) {
    const collection = mongoose.connection.collections[collectionName];
    if (collection) {
      await collection.insertMany(documents);
    }
  }
}

module.exports = TestDatabase;
```

## Test Data Factories

### User Factory

```javascript
// tests/helpers/factories.js
const mongoose = require("mongoose");
const bcrypt = require("bcrypt");

class UserFactory {
  static async create(overrides = {}) {
    const User = mongoose.model("User");

    const defaultData = {
      name: "Test User",
      email: `test${Date.now()}@example.com`,
      password: await bcrypt.hash("password123", 10),
      role: "user",
      isEmailVerified: true,
    };

    const userData = { ...defaultData, ...overrides };
    const user = await User.create(userData);

    return user;
  }

  static async createMany(count, overrides = {}) {
    const users = [];
    for (let i = 0; i < count; i++) {
      users.push(
        await this.create({
          ...overrides,
          email: `test${Date.now()}_${i}@example.com`,
        }),
      );
    }
    return users;
  }
}

class WorkflowFactory {
  static async create(userId, overrides = {}) {
    const Workflow = mongoose.model("Workflow");

    const defaultData = {
      userId,
      name: "Test Workflow",
      source: "mailchimp",
      destination: "klaviyo",
      status: "pending",
      actions: [
        {
          function: "migrate_contacts",
          parameters: {},
        },
      ],
    };

    const workflowData = { ...defaultData, ...overrides };
    const workflow = await Workflow.create(workflowData);

    return workflow;
  }
}

module.exports = { UserFactory, WorkflowFactory };
```

## Unit Tests

### Testing Services

```javascript
// tests/unit/services/auth.test.js
const AuthService = require("../../../services/AuthService");
const { UserFactory } = require("../../helpers/factories");
const jwt = require("jsonwebtoken");

describe("AuthService", () => {
  describe("generateToken", () => {
    it("should generate valid JWT token", async () => {
      const user = await UserFactory.create();

      const token = AuthService.generateToken(user);

      expect(token).toBeDefined();
      expect(typeof token).toBe("string");

      // Verify token
      const decoded = jwt.verify(token, process.env.JWT_SECRET);
      expect(decoded.userId).toBe(user._id.toString());
    });

    it("should include user role in token", async () => {
      const user = await UserFactory.create({ role: "admin" });

      const token = AuthService.generateToken(user);
      const decoded = jwt.verify(token, process.env.JWT_SECRET);

      expect(decoded.role).toBe("admin");
    });
  });

  describe("verifyPassword", () => {
    it("should return true for correct password", async () => {
      const user = await UserFactory.create();

      const isValid = await AuthService.verifyPassword(
        "password123",
        user.password,
      );

      expect(isValid).toBe(true);
    });

    it("should return false for incorrect password", async () => {
      const user = await UserFactory.create();

      const isValid = await AuthService.verifyPassword(
        "wrongpassword",
        user.password,
      );

      expect(isValid).toBe(false);
    });
  });
});
```

### Testing Utilities

```javascript
// tests/unit/utils/encryption.test.js
const { encrypt, decrypt } = require("../../../utils/encryption");

describe("Encryption Utils", () => {
  describe("encrypt and decrypt", () => {
    it("should encrypt and decrypt text correctly", () => {
      const plainText = "my-secret-api-key";
      const key = Buffer.from("a".repeat(32), "utf8");

      const encrypted = encrypt(plainText, key);
      const decrypted = decrypt(encrypted, key);

      expect(decrypted).toBe(plainText);
    });

    it("should fail to decrypt with wrong key", () => {
      const plainText = "my-secret-api-key";
      const key1 = Buffer.from("a".repeat(32), "utf8");
      const key2 = Buffer.from("b".repeat(32), "utf8");

      const encrypted = encrypt(plainText, key1);

      expect(() => decrypt(encrypted, key2)).toThrow();
    });

    it("should generate different encrypted values for same input", () => {
      const plainText = "my-secret-api-key";
      const key = Buffer.from("a".repeat(32), "utf8");

      const encrypted1 = encrypt(plainText, key);
      const encrypted2 = encrypt(plainText, key);

      // Different due to IV
      expect(encrypted1).not.toBe(encrypted2);

      // But both decrypt to same value
      expect(decrypt(encrypted1, key)).toBe(plainText);
      expect(decrypt(encrypted2, key)).toBe(plainText);
    });
  });
});
```

## Integration Tests

### Testing API Endpoints

```javascript
// tests/integration/auth.test.js
const request = require("supertest");
const app = require("../../app");
const { UserFactory } = require("../helpers/factories");

describe("POST /api/v1/auth/login", () => {
  it("should login with valid credentials", async () => {
    const user = await UserFactory.create({
      email: "test@example.com",
      password: await bcrypt.hash("password123", 10),
    });

    const response = await request(app).post("/api/v1/auth/login").send({
      email: "test@example.com",
      password: "password123",
    });

    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);
    expect(response.body.token).toBeDefined();
    expect(response.body.user).toBeDefined();
    expect(response.body.user.email).toBe("test@example.com");
  });

  it("should return 401 for invalid email", async () => {
    const response = await request(app).post("/api/v1/auth/login").send({
      email: "nonexistent@example.com",
      password: "password123",
    });

    expect(response.status).toBe(401);
    expect(response.body.success).toBe(false);
    expect(response.body.error).toBe("Invalid credentials");
  });

  it("should return 401 for invalid password", async () => {
    await UserFactory.create({
      email: "test@example.com",
    });

    const response = await request(app).post("/api/v1/auth/login").send({
      email: "test@example.com",
      password: "wrongpassword",
    });

    expect(response.status).toBe(401);
    expect(response.body.success).toBe(false);
  });

  it("should validate required fields", async () => {
    const response = await request(app).post("/api/v1/auth/login").send({
      email: "test@example.com",
      // Missing password
    });

    expect(response.status).toBe(400);
    expect(response.body.error).toContain("password");
  });
});
```

### Testing Protected Routes

```javascript
// tests/integration/workflows.test.js
const request = require("supertest");
const app = require("../../app");
const { UserFactory, WorkflowFactory } = require("../helpers/factories");
const AuthService = require("../../services/AuthService");

describe("GET /api/v1/workflows", () => {
  let user, token;

  beforeEach(async () => {
    user = await UserFactory.create();
    token = AuthService.generateToken(user);
  });

  it("should return user workflows", async () => {
    // Create workflows for this user
    await WorkflowFactory.create(user._id, { name: "Workflow 1" });
    await WorkflowFactory.create(user._id, { name: "Workflow 2" });

    // Create workflow for another user (should not be returned)
    const otherUser = await UserFactory.create();
    await WorkflowFactory.create(otherUser._id, { name: "Other Workflow" });

    const response = await request(app)
      .get("/api/v1/workflows")
      .set("Authorization", `Bearer ${token}`);

    expect(response.status).toBe(200);
    expect(response.body.workflows).toHaveLength(2);
    expect(response.body.workflows[0].name).toBe("Workflow 1");
    expect(response.body.workflows[1].name).toBe("Workflow 2");
  });

  it("should return 401 without token", async () => {
    const response = await request(app).get("/api/v1/workflows");

    expect(response.status).toBe(401);
  });

  it("should return 401 with invalid token", async () => {
    const response = await request(app)
      .get("/api/v1/workflows")
      .set("Authorization", "Bearer invalid-token");

    expect(response.status).toBe(401);
  });
});
```

## Mocking External Services

### Mocking HTTP Requests (nock)

```javascript
// tests/integration/oauth.test.js
const nock = require("nock");

describe("POST /api/v1/oauth/klaviyo/callback", () => {
  afterEach(() => {
    nock.cleanAll();
  });

  it("should exchange code for tokens", async () => {
    const user = await UserFactory.create();
    const token = AuthService.generateToken(user);

    // Mock Klaviyo token exchange
    nock("https://a.klaviyo.com").post("/oauth/token").reply(200, {
      access_token: "mock_access_token",
      refresh_token: "mock_refresh_token",
      expires_in: 3600,
      token_type: "Bearer",
    });

    const response = await request(app)
      .post("/api/v1/oauth/klaviyo/callback")
      .set("Authorization", `Bearer ${token}`)
      .send({
        code: "mock_authorization_code",
        state: "mock_state",
      });

    expect(response.status).toBe(200);
    expect(response.body.success).toBe(true);

    // Verify connection was saved
    const OAuthConnection = mongoose.model("OAuthConnection");
    const connection = await OAuthConnection.findOne({ userId: user._id });
    expect(connection).toBeDefined();
    expect(connection.provider).toBe("klaviyo");
  });

  it("should handle token exchange failure", async () => {
    const user = await UserFactory.create();
    const token = AuthService.generateToken(user);

    // Mock failed token exchange
    nock("https://a.klaviyo.com").post("/oauth/token").reply(400, {
      error: "invalid_grant",
      error_description: "Authorization code expired",
    });

    const response = await request(app)
      .post("/api/v1/oauth/klaviyo/callback")
      .set("Authorization", `Bearer ${token}`)
      .send({
        code: "expired_code",
        state: "mock_state",
      });

    expect(response.status).toBe(400);
    expect(response.body.error).toContain("invalid_grant");
  });
});
```

### Mocking Services

```javascript
// tests/unit/controllers/paymentController.test.js
jest.mock("../../../services/StripeService");
const StripeService = require("../../../services/StripeService");

describe("PaymentController", () => {
  describe("createPaymentIntent", () => {
    it("should create payment intent", async () => {
      // Mock Stripe service
      StripeService.createPaymentIntent.mockResolvedValue({
        id: "pi_test_123",
        client_secret: "pi_test_123_secret",
        amount: 1000,
        currency: "usd",
      });

      const user = await UserFactory.create();
      const token = AuthService.generateToken(user);

      const response = await request(app)
        .post("/api/v1/payments/create-intent")
        .set("Authorization", `Bearer ${token}`)
        .send({
          amount: 1000,
          currency: "usd",
        });

      expect(response.status).toBe(200);
      expect(response.body.clientSecret).toBe("pi_test_123_secret");
      expect(StripeService.createPaymentIntent).toHaveBeenCalledWith({
        amount: 1000,
        currency: "usd",
        customerId: user.stripeCustomerId,
      });
    });
  });
});
```

## Testing Error Scenarios

### Testing Validation Errors

```javascript
describe("POST /api/v1/workflows", () => {
  let user, token;

  beforeEach(async () => {
    user = await UserFactory.create();
    token = AuthService.generateToken(user);
  });

  it("should validate required fields", async () => {
    const response = await request(app)
      .post("/api/v1/workflows")
      .set("Authorization", `Bearer ${token}`)
      .send({
        // Missing required fields
      });

    expect(response.status).toBe(400);
    expect(response.body.error).toBeDefined();
    expect(response.body.errors).toContain("name is required");
  });

  it("should validate enum values", async () => {
    const response = await request(app)
      .post("/api/v1/workflows")
      .set("Authorization", `Bearer ${token}`)
      .send({
        name: "Test Workflow",
        source: "invalid_platform",
        destination: "klaviyo",
      });

    expect(response.status).toBe(400);
    expect(response.body.errors).toContain(
      "source must be one of: mailchimp, klaviyo, yotpo",
    );
  });
});
```

### Testing Database Errors

```javascript
describe("Database Error Handling", () => {
  it("should handle duplicate key error", async () => {
    const user = await UserFactory.create({ email: "test@example.com" });

    // Try to create another user with same email
    const response = await request(app).post("/api/v1/auth/register").send({
      name: "Test User 2",
      email: "test@example.com",
      password: "password123",
    });

    expect(response.status).toBe(400);
    expect(response.body.error).toContain("email already exists");
  });

  it("should handle validation errors", async () => {
    const response = await request(app).post("/api/v1/auth/register").send({
      name: "Test User",
      email: "invalid-email",
      password: "short",
    });

    expect(response.status).toBe(400);
    expect(response.body.errors).toBeDefined();
  });
});
```

## Testing Async Operations

### Testing Background Jobs

```javascript
// tests/unit/workers/migrationWorker.test.js
const MigrationWorker = require("../../../workers/migrationWorker");
const nativeAppService = require("../../../services/nativeAppService");

jest.mock("../../../services/nativeAppService");

describe("MigrationWorker", () => {
  it("should process migration job", async () => {
    nativeAppService.submitJob.mockResolvedValue({
      job_id: "job_123",
    });

    nativeAppService.getJobStatus.mockResolvedValue({
      status: "success",
      result: {
        migrated_count: 100,
      },
    });

    const workflow = await WorkflowFactory.create(user._id);

    await MigrationWorker.processMigration(workflow._id);

    // Verify workflow was updated
    const updatedWorkflow = await Workflow.findById(workflow._id);
    expect(updatedWorkflow.status).toBe("completed");
    expect(updatedWorkflow.result.migrated_count).toBe(100);
  });

  it("should handle job failure", async () => {
    nativeAppService.submitJob.mockResolvedValue({
      job_id: "job_123",
    });

    nativeAppService.getJobStatus.mockResolvedValue({
      status: "failed",
      error: "Timeout waiting for element",
    });

    const workflow = await WorkflowFactory.create(user._id);

    await MigrationWorker.processMigration(workflow._id);

    const updatedWorkflow = await Workflow.findById(workflow._id);
    expect(updatedWorkflow.status).toBe("failed");
    expect(updatedWorkflow.error).toContain("Timeout");
  });
});
```

## Test Coverage

### Running Tests with Coverage

```bash
# Run all tests with coverage
npm test -- --coverage

# Run specific test file
npm test -- auth.test.js

# Watch mode for development
npm test -- --watch

# Run only changed tests
npm test -- --onlyChanged
```

### Coverage Configuration

```javascript
// jest.config.js
module.exports = {
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
  coverageReporters: ["text", "lcov", "html"],
};
```

### Viewing Coverage Report

```bash
# Generate coverage report
npm test -- --coverage

# Open HTML report
open coverage/lcov-report/index.html
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      mongodb:
        image: mongo:5.0
        ports:
          - 27017:27017

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: "18"

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test -- --coverage --ci

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info
```

## Best Practices

1. **Use factories** for test data instead of hard-coded values
2. **Mock external services** - don't make real API calls in tests
3. **Clean database** between tests to avoid test pollution
4. **Test error paths** - don't just test happy paths
5. **Use descriptive test names** - describe what is being tested
6. **Keep tests independent** - tests should not depend on each other
7. **Test one thing per test** - focused, atomic tests
8. **Use beforeEach/afterEach** for setup and cleanup
9. **Maintain high coverage** - aim for 80%+ code coverage
10. **Run tests in CI/CD** - catch regressions early

## Common Pitfalls

❌ **Forgetting to clean up database**

```javascript
// BAD: Tests pollute each other
test("create user", async () => {
  await User.create({ email: "test@example.com" });
});
// Next test will fail if it creates same email
```

✅ **Clean database between tests**

```javascript
// GOOD: Clean state for each test
afterEach(async () => {
  await TestDatabase.clearAllCollections();
});
```

❌ **Making real API calls**

```javascript
// BAD: Slow, unreliable, costs money
const response = await axios.post("https://api.stripe.com/v1/charges", {
  amount: 1000,
});
```

✅ **Mock external services**

```javascript
// GOOD: Fast, reliable, free
nock("https://api.stripe.com").post("/v1/charges").reply(200, {
  id: "ch_test_123",
});
```

## Next Steps

- See `structuring-clean-architecture` for organizing testable code
- Check `validating-joi-schemas` for request validation testing
- Review `implementing-oauth-flows` for OAuth testing patterns
- See `reference/testing-best-practices.md` for advanced patterns
