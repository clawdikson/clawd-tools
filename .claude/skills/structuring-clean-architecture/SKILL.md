---
name: structuring-clean-architecture
description: Organize Node.js/Express backend code following Clean Architecture principles with proper layer separation (Application, Infrastructure, Interface). Use when adding major features, refactoring modules, or maintaining dependency inversion for the automation backend.
---

# Structuring Clean Architecture

Organize backend code following Clean Architecture principles in the automation workflow backend. Maintain proper layer separation and dependency direction.

## When to Use This Skill

- Adding new major features or modules
- Refactoring existing code for better organization
- Creating new use cases, repositories, or controllers
- Ensuring dependency inversion is maintained
- Understanding where new code should be placed

## Architecture Layers

```
src/
├── application/          # Business Logic Layer (Layer 2)
│   ├── services/         # Application services
│   ├── useCases/         # Business use cases
│   └── joiValidations/   # Request validation
│
├── infrastructure/       # External Dependencies Layer (Layer 1)
│   ├── config/           # Configuration
│   ├── database/         # Database connections & models
│   ├── repositories/     # Data access implementations
│   ├── jobs/             # Background jobs
│   └── logging/          # Logging utilities
│
└── interfaces/           # Adapters Layer (Layer 3)
    └── http/             # HTTP interface
        ├── controllers/  # Route handlers
        ├── middlewares/  # HTTP middlewares
        ├── routes/       # Route definitions
        └── server.js     # Express setup
```

### Dependency Rules

**Core Principle**: Dependencies point inward

- **Interfaces** → **Application** → **Infrastructure** ✅
- **Infrastructure** → **Application** ❌ (violates Clean Architecture)

## Layer 1: Infrastructure (External Dependencies)

### Purpose

Handle all external dependencies: databases, file systems, third-party APIs, logging.

### What Goes Here

**Database Models** (`infrastructure/database/mongodb/models/`):

```javascript
const mongoose = require("mongoose");

const userSchema = new mongoose.Schema(
  {
    email: { type: String, required: true, unique: true },
    role: { type: String, enum: ["admin", "user", "worker"] },
  },
  { timestamps: true },
);

module.exports = mongoose.model("User", userSchema);
```

**Repositories** (`infrastructure/repositories/`):

```javascript
// userRepository.js
const User = require("../database/mongodb/models/User");

class UserRepository {
  async findById(id) {
    return User.findById(id);
  }

  async create(userData) {
    return User.create(userData);
  }

  async findByEmail(email) {
    return User.findOne({ email });
  }
}

module.exports = new UserRepository();
```

**Configuration** (`infrastructure/config/`):

```javascript
// index.js
module.exports = {
  port: process.env.PORT || 5000,
  mongodb: {
    uri: process.env.MONGODB_URI,
  },
  jwt: {
    secret: process.env.JWT_SECRET,
    expiresIn: "7d",
  },
};
```

**Background Jobs** (`infrastructure/jobs/`):

```javascript
// oauthTokenRefresh.js
const cron = require("node-cron");

function startTokenRefreshJob() {
  cron.schedule("*/5 * * * *", async () => {
    // Job logic
  });
}

module.exports = { startTokenRefreshJob };
```

## Layer 2: Application (Business Logic)

### Purpose

Contains business rules and application-specific logic. No framework dependencies.

### What Goes Here

**Use Cases** (`application/useCases/`):

```javascript
// useCases/user/createUser.js
const userRepository = require("../../../infrastructure/repositories/userRepository");
const bcrypt = require("bcryptjs");

module.exports = async function createUser({ email, password, role }) {
  // Business logic
  const existingUser = await userRepository.findByEmail(email);

  if (existingUser) {
    throw new Error("User already exists");
  }

  const hashedPassword = await bcrypt.hash(password, 10);

  const user = await userRepository.create({
    email,
    password: hashedPassword,
    role: role || "user",
  });

  return {
    id: user._id,
    email: user.email,
    role: user.role,
  };
};
```

**Services** (`application/services/`):

```javascript
// services/oauthService.js
const crypto = require("crypto");

class OAuthService {
  static generatePKCE() {
    const codeVerifier = crypto.randomBytes(32).toString("base64url");
    const codeChallenge = crypto
      .createHash("sha256")
      .update(codeVerifier)
      .digest("base64url");

    return { codeVerifier, codeChallenge };
  }
}

module.exports = OAuthService;
```

**Validation Schemas** (`application/joiValidations/`):

```javascript
// userValidation.js
const Joi = require("joi");

const createUserSchema = Joi.object({
  email: Joi.string().email().required(),
  password: Joi.string().min(8).required(),
  role: Joi.string().valid("admin", "user", "worker").optional(),
});

module.exports = { createUserSchema };
```

## Layer 3: Interfaces (Adapters)

### Purpose

Adapt external interfaces (HTTP, CLI, etc.) to application layer.

### What Goes Here

**Controllers** (`interfaces/http/controllers/`):

```javascript
// userController.js
const createUser = require("../../../application/useCases/user/createUser");
const httpStatus = require("http-status");

exports.createUser = async (req, res, next) => {
  try {
    const { email, password, role } = req.body;

    const user = await createUser({ email, password, role });

    res.status(httpStatus.CREATED).json({
      success: true,
      data: user,
    });
  } catch (error) {
    next(error);
  }
};
```

**Routes** (`interfaces/http/routes/`):

```javascript
// userRoutes.js
const express = require("express");
const router = express.Router();
const userController = require("../controllers/userController");
const { validateRequest } = require("../middlewares/validation");
const {
  createUserSchema,
} = require("../../../application/joiValidations/userValidation");
const { authenticate } = require("../middlewares/auth");

router.post(
  "/users",
  authenticate,
  validateRequest(createUserSchema),
  userController.createUser,
);

module.exports = router;
```

**Middlewares** (`interfaces/http/middlewares/`):

```javascript
// validation.js
const httpStatus = require("http-status");

exports.validateRequest = (schema) => {
  return (req, res, next) => {
    const { error } = schema.validate(req.body);

    if (error) {
      return res.status(httpStatus.BAD_REQUEST).json({
        success: false,
        error: error.details[0].message,
      });
    }

    next();
  };
};
```

## Adding New Features

### Step 1: Define Use Case (Application Layer)

```javascript
// application/useCases/workflow/createWorkflow.js
const workflowRepository = require("../../../infrastructure/repositories/workflowRepository");

module.exports = async function createWorkflow({ name, steps, userId }) {
  // Validate business rules
  if (steps.length === 0) {
    throw new Error("Workflow must have at least one step");
  }

  // Create workflow
  const workflow = await workflowRepository.create({
    name,
    steps,
    userId,
    status: "draft",
  });

  return workflow;
};
```

### Step 2: Create Repository (Infrastructure Layer)

```javascript
// infrastructure/repositories/workflowRepository.js
const Workflow = require("../database/mongodb/models/Workflow");

class WorkflowRepository {
  async create(workflowData) {
    return Workflow.create(workflowData);
  }

  async findByUserId(userId) {
    return Workflow.find({ userId });
  }

  async update(id, updates) {
    return Workflow.findByIdAndUpdate(id, updates, { new: true });
  }
}

module.exports = new WorkflowRepository();
```

### Step 3: Add Controller (Interface Layer)

```javascript
// interfaces/http/controllers/workflowController.js
const createWorkflow = require("../../../application/useCases/workflow/createWorkflow");

exports.createWorkflow = async (req, res, next) => {
  try {
    const { name, steps } = req.body;
    const userId = req.user.id;

    const workflow = await createWorkflow({ name, steps, userId });

    res.status(201).json({
      success: true,
      data: workflow,
    });
  } catch (error) {
    next(error);
  }
};
```

### Step 4: Define Routes (Interface Layer)

```javascript
// interfaces/http/routes/workflowRoutes.js
const express = require("express");
const router = express.Router();
const workflowController = require("../controllers/workflowController");
const { authenticate } = require("../middlewares/auth");

router.post("/workflows", authenticate, workflowController.createWorkflow);

module.exports = router;
```

## Organizing Use Cases

### By Domain

```
application/useCases/
├── user/
│   ├── createUser.js
│   ├── updateUser.js
│   └── deleteUser.js
├── workflow/
│   ├── createWorkflow.js
│   ├── executeWorkflow.js
│   └── updateWorkflow.js
└── oauth/
    ├── initiateOAuth.js
    ├── handleCallback.js
    └── refreshToken.js
```

### Use Case Template

```javascript
/**
 * Use Case: [Action Description]
 *
 * Purpose: [What business problem this solves]
 *
 * Dependencies:
 * - Repository: [Which repositories]
 * - Services: [Which services]
 *
 * Returns: [What it returns]
 * Throws: [What errors it can throw]
 */

const repository = require("../../../infrastructure/repositories/...");

module.exports = async function useCaseName({ param1, param2 }) {
  // 1. Validate business rules
  // 2. Execute business logic
  // 3. Return result
};
```

## Common Patterns

### Pattern 1: Transaction Management

```javascript
// Use case with transaction
module.exports = async function transferWorkflow({
  workflowId,
  fromUserId,
  toUserId,
}) {
  const session = await mongoose.startSession();
  session.startTransaction();

  try {
    // Business logic with session
    await workflowRepository.update(
      workflowId,
      { userId: toUserId },
      { session },
    );
    await auditRepository.log({ action: "transfer", workflowId }, { session });

    await session.commitTransaction();
  } catch (error) {
    await session.abortTransaction();
    throw error;
  } finally {
    session.endSession();
  }
};
```

### Pattern 2: Service Composition

```javascript
// application/services/workflowService.js
class WorkflowService {
  constructor(workflowRepository, notificationService) {
    this.workflowRepository = workflowRepository;
    this.notificationService = notificationService;
  }

  async executeWorkflow(workflowId) {
    const workflow = await this.workflowRepository.findById(workflowId);

    // Execute workflow steps

    // Notify on completion
    await this.notificationService.send({
      type: "workflow_complete",
      workflowId,
    });
  }
}
```

### Pattern 3: Repository Pattern with Caching

```javascript
class CachedUserRepository {
  constructor(userRepository, cache) {
    this.userRepository = userRepository;
    this.cache = cache;
  }

  async findById(id) {
    const cached = await this.cache.get(`user:${id}`);
    if (cached) return cached;

    const user = await this.userRepository.findById(id);
    await this.cache.set(`user:${id}`, user, 3600);
    return user;
  }
}
```

## Testing by Layer

### Application Layer Tests (Unit Tests)

```javascript
// createUser.test.js
const createUser = require("./createUser");
const userRepository = require("../../../infrastructure/repositories/userRepository");

jest.mock("../../../infrastructure/repositories/userRepository");

describe("createUser", () => {
  it("should create user with hashed password", async () => {
    userRepository.findByEmail.mockResolvedValue(null);
    userRepository.create.mockResolvedValue({
      _id: "123",
      email: "test@example.com",
    });

    const result = await createUser({
      email: "test@example.com",
      password: "password123",
    });

    expect(result.email).toBe("test@example.com");
  });
});
```

### Interface Layer Tests (Integration Tests)

```javascript
// userController.test.js
const request = require("supertest");
const app = require("../server");

describe("POST /api/v1/users", () => {
  it("should create user and return 201", async () => {
    const response = await request(app)
      .post("/api/v1/users")
      .send({
        email: "test@example.com",
        password: "password123",
      })
      .expect(201);

    expect(response.body.success).toBe(true);
  });
});
```

## Common Mistakes to Avoid

❌ **Putting business logic in controllers**

```javascript
// BAD: Business logic in controller
exports.createUser = async (req, res) => {
  const hashedPassword = await bcrypt.hash(req.body.password, 10);
  const user = await User.create({ ...req.body, password: hashedPassword });
  // ...
};
```

✅ **Keep controllers thin**

```javascript
// GOOD: Delegate to use case
exports.createUser = async (req, res, next) => {
  try {
    const user = await createUser(req.body);
    res.status(201).json({ success: true, data: user });
  } catch (error) {
    next(error);
  }
};
```

❌ **Use cases depending on HTTP concepts**

```javascript
// BAD: Use case knows about HTTP
module.exports = async function createUser(req, res) {
  // ...
  res.status(201).json({ user });
};
```

✅ **Use cases are framework-agnostic**

```javascript
// GOOD: Pure business logic
module.exports = async function createUser({ email, password }) {
  // ...
  return user; // Just return data
};
```

## Migration Strategy

When refactoring existing code:

1. **Start with use cases** - Extract business logic first
2. **Create repositories** - Abstract data access
3. **Thin controllers** - Make controllers simple adapters
4. **Move validation** - Joi schemas to application layer
5. **Test progressively** - Ensure each layer works independently

## Best Practices

1. **One use case per file** - Single responsibility
2. **Use case names are verbs** - createUser, updateWorkflow, deleteProject
3. **Repository methods are simple** - find, create, update, delete
4. **Controllers are thin** - Just adapt HTTP to use cases
5. **No framework in application layer** - Pure JavaScript/Node
6. **Mock external dependencies** - Easy testing
7. **Dependency injection** - Pass dependencies to constructors

## Next Steps

- See `reference/layer-examples.md` for complete feature examples
- Check `reference/migration-guide.md` for refactoring existing code
- Review `reference/testing-strategies.md` for layer-specific testing
