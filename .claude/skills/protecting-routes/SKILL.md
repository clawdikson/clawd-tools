# protecting-routes

## Description

Implement authentication and authorization middleware for protecting Express.js routes in the Node.js backend. Covers JWT token verification, role-based access control (RBAC), route-level and router-level protection, and error handling for unauthorized access.

## When to Use

- Adding new protected API endpoints that require authentication
- Implementing role-based access control for admin/user/worker routes
- Protecting existing public routes with authentication
- Debugging authentication or authorization issues
- Implementing multi-role access patterns (e.g., admin OR super_admin)
- Understanding how JWT tokens are verified and users are attached to requests

## Prerequisites

- Understanding of JWT authentication flow
- Basic knowledge of Express.js middleware
- Familiarity with the backend's role system (admin, user, worker, dev, super_admin)
- Understanding of HTTP status codes (401 Unauthorized, 403 Forbidden)

## Key Concepts

### Authentication vs Authorization

- **Authentication** (`checkJWTToken`): Verifying the user's identity via JWT token
- **Authorization** (`checkRole`, `checkAnyRoles`): Verifying the authenticated user has required permissions

### Middleware Location

All authentication middleware is located in:

```
src/interfaces/http/middlewares/auth.js
```

### Available Middleware Functions

1. **checkJWTToken** - Verifies JWT token and attaches user to `req.user`
2. **checkRole(role)** - Requires user to have specific role
3. **checkAnyRoles([roles])** - Requires user to have any of the specified roles

## Implementation Patterns

### 1. JWT Token Verification

The `checkJWTToken` middleware verifies JWT tokens from the `Authorization` header:

```javascript
// src/interfaces/http/middlewares/auth.js
const jwt = require("jsonwebtoken");
const httpStatus = require("http-status");
const { ApplicationError } = require("./errorHandler");
const userRepository = require("../../../infrastructure/repositories/userRepository");
const config = require("../../../infrastructure/config");

const checkJWTToken = async (req, res, next) => {
  try {
    // Extract token from Authorization header (format: "Bearer <token>")
    const token = req.headers.authorization?.split(" ")[1];
    if (!token) {
      throw new ApplicationError("No token provided", httpStatus.UNAUTHORIZED);
    }

    // Verify token signature and decode payload
    const decoded = jwt.verify(token, config.jwtSecret);

    // Get user from database
    const user = await userRepository.findOne(decoded.id);
    if (!user) {
      throw new ApplicationError("User not found", httpStatus.UNAUTHORIZED);
    }

    // Get user's roles
    const roles = await userRepository.getRole(user._id);

    // Attach user and roles to request object for downstream middleware/controllers
    req.user = user;
    req.user.roles = roles;
    next();
  } catch (error) {
    // Handle JWT-specific errors
    if (error.name === "JsonWebTokenError") {
      next(new ApplicationError("Invalid token", 401));
    } else if (error.name === "TokenExpiredError") {
      next(new ApplicationError("Token expired", 401));
    } else {
      next(error);
    }
  }
};
```

**What it does**:

- Extracts JWT from `Authorization: Bearer <token>` header
- Verifies token signature using `config.jwtSecret`
- Fetches user from database to ensure they still exist
- Fetches user's roles for authorization checks
- Attaches `req.user` (with roles) for use in controllers
- Returns 401 for missing, invalid, or expired tokens

### 2. Single Role Check

The `checkRole` middleware requires a specific role:

```javascript
const checkRole = (role) => {
  return (req, res, next) => {
    const roles = req.user?.roles?.filter(
      (userRole) => userRole.roleLevel == role,
    );
    if (!roles.length) {
      next(new ApplicationError("Unauthorized", httpStatus.FORBIDDEN));
    }
    next();
  };
};
```

**Usage**:

```javascript
// Worker-only route
router.get(
  "/projects",
  authMiddleware.checkJWTToken,
  authMiddleware.checkRole(ROLES.WORKER),
  workerController.getProjects,
);

// Dev-only route
router.use(authMiddleware.checkJWTToken, authMiddleware.checkRole(ROLES.DEV)); // Applies to all routes below
```

### 3. Multiple Role Check

The `checkAnyRoles` middleware allows access if user has ANY of the specified roles:

```javascript
const checkAnyRoles = (roleLevels) => {
  return (req, res, next) => {
    if (!req.user?.roles || !Array.isArray(req.user.roles)) {
      return next(
        new ApplicationError(
          "Unauthorized - No roles found",
          httpStatus.FORBIDDEN,
        ),
      );
    }

    const hasAnyRole = req.user.roles.some((role) =>
      roleLevels.includes(role.roleLevel),
    );

    if (!hasAnyRole) {
      return next(
        new ApplicationError(
          "Unauthorized - Insufficient permissions",
          httpStatus.FORBIDDEN,
        ),
      );
    }
    next();
  };
};

module.exports = {
  checkJWTToken,
  checkRole,
  checkAnyRoles,
};
```

**Usage**:

```javascript
// Admin OR super_admin can access
router.use(authMiddleware.checkAnyRoles([ROLES.ADMIN, ROLES.SUPER_ADMIN]));
```

## Route Protection Patterns

### Pattern 1: Route-Level Protection

Apply middleware to individual routes:

```javascript
// src/interfaces/http/routes/oauthRoutes.js
const { Router } = require("express");
const authMiddleware = require("../middlewares/auth");
const oauthController = require("../controllers/oauthController");

const router = Router();

// Public routes (no protection)
router.get("/klaviyo/callback", oauthController.handleKlaviyoCallback);

// Protected routes (authentication required)
router.post(
  "/klaviyo/connect",
  authMiddleware.checkJWTToken,
  oauthController.initiateKlaviyoOAuth,
);

router.post(
  "/klaviyo/refresh",
  authMiddleware.checkJWTToken,
  oauthController.refreshKlaviyoToken,
);

router.delete(
  "/klaviyo/disconnect",
  authMiddleware.checkJWTToken,
  oauthController.disconnectKlaviyo,
);

router.get(
  "/klaviyo/status",
  authMiddleware.checkJWTToken,
  oauthController.getKlaviyoStatus,
);

module.exports = router;
```

### Pattern 2: Router-Level Protection

Apply middleware to all routes in a router using `router.use()`:

```javascript
// src/interfaces/http/routes/adminRoutes.js
const { Router } = require("express");
const AdminController = require("../controllers/adminController");
const authMiddleware = require("../middlewares/auth");
const { ROLES } = require("../../../constants");

const router = Router();
const adminController = new AdminController();

// First middleware: Authenticate all routes
router.use(authMiddleware.checkJWTToken);

// Public authenticated route (any authenticated user)
router.get("/me", adminController.getUserById);

// Second middleware: Authorize only admin/super_admin for routes below
router.use(authMiddleware.checkAnyRoles([ROLES.ADMIN, ROLES.SUPER_ADMIN]));

// Admin-only routes
router.get("/workflows", adminController.getUserWorkflowsHandler);
router.get("/recipes", adminController.getUserRecipesHandler);
router.get("/actions", adminController.getUserActionsHandler);
router.get("/workflows/:id", adminController.getUserWorkflowByIdHandler);
router.put("/workflows/:id", adminController.updateUserWorkflowHandler);
router.delete("/workflows/:id", adminController.deleteUserWorkflowHandler);

module.exports = router;
```

**Key Pattern**:

1. `router.use(checkJWTToken)` - All routes require authentication
2. Public route (`/me`) - Any authenticated user
3. `router.use(checkAnyRoles([...]))` - Routes below require admin roles
4. Admin routes - Only admin/super_admin can access

### Pattern 3: Multiple Middleware Chain

Apply multiple middleware in sequence:

```javascript
// Worker-only routes
router.use(
  authMiddleware.checkJWTToken,
  authMiddleware.checkRole(ROLES.WORKER),
);

router.get("/projects", workerController.getProjects);
router.post("/projects/:id/complete", workerController.completeProject);
```

### Pattern 4: Wildcard Route Protection

Protect all subroutes with wildcard:

```javascript
// Proxy all Klaviyo API requests (any HTTP method, any path)
router.all(
  "/api/*",
  authMiddleware.checkJWTToken,
  klaviyoApiController.proxyRequest,
);
```

## Role Constants

Roles are defined in `src/constants/index.js`:

```javascript
const ROLES = {
  SUPER_ADMIN: "superAdmin",
  ADMIN: "admin",
  WORKER: "worker",
  DEV: "dev",
};

module.exports = { ROLES };
```

**Role Hierarchy** (implicit in application logic):

1. **SUPER_ADMIN** - Highest privileges, all admin capabilities
2. **ADMIN** - Standard admin, workflow management
3. **WORKER** - Limited access, project execution
4. **DEV** - Development/debugging routes

**Usage**:

```javascript
const { ROLES } = require("../../../constants");

// Single role
router.use(authMiddleware.checkRole(ROLES.ADMIN));

// Multiple roles
router.use(authMiddleware.checkAnyRoles([ROLES.ADMIN, ROLES.SUPER_ADMIN]));
```

## Accessing Authenticated User in Controllers

After `checkJWTToken` runs, `req.user` contains the authenticated user:

```javascript
// src/interfaces/http/controllers/oauthController.js
class OAuthController {
  async initiateKlaviyoOAuth(req, res, next) {
    try {
      // req.user is available after checkJWTToken middleware
      const userId = req.user._id;
      const userEmail = req.user.email;
      const userRoles = req.user.roles; // Array of role objects

      // Use user info for authorization logic
      const result = await this.oauthService.initiateKlaviyo(userId);

      res.status(httpStatus.OK).json({
        status: "success",
        data: result,
      });
    } catch (error) {
      next(error);
    }
  }

  async getKlaviyoStatus(req, res, next) {
    try {
      const userId = req.user._id;

      // Only return status for the authenticated user
      const status = await this.oauthService.getConnectionStatus(userId);

      res.status(httpStatus.OK).json({
        status: "success",
        data: status,
      });
    } catch (error) {
      next(error);
    }
  }
}
```

## Error Responses

### 401 Unauthorized (Authentication Failed)

Returned when JWT verification fails:

```json
{
  "status": "error",
  "message": "No token provided",
  "statusCode": 401
}
```

```json
{
  "status": "error",
  "message": "Invalid token",
  "statusCode": 401
}
```

```json
{
  "status": "error",
  "message": "Token expired",
  "statusCode": 401
}
```

**Common Causes**:

- Missing `Authorization` header
- Invalid token format (not `Bearer <token>`)
- Token signature invalid
- Token expired
- User no longer exists in database

### 403 Forbidden (Authorization Failed)

Returned when user is authenticated but lacks required role:

```json
{
  "status": "error",
  "message": "Unauthorized",
  "statusCode": 403
}
```

```json
{
  "status": "error",
  "message": "Unauthorized - Insufficient permissions",
  "statusCode": 403
}
```

**Common Causes**:

- User authenticated but doesn't have required role
- User has `user` role but route requires `admin`
- User's role was revoked after token issued

## Complete Route File Example

```javascript
// src/interfaces/http/routes/paymentRoutes.js
const { Router } = require("express");
const PaymentController = require("../controllers/paymentController");
const authMiddleware = require("../middlewares/auth");

const router = Router();
const paymentController = new PaymentController();

// Public route (no authentication)
router.get("/health", paymentController.checkHealth);

// Protected routes (authentication required)
router.post(
  "/migration",
  authMiddleware.checkJWTToken,
  paymentController.createMigrationPayment,
);

router.put(
  "/migration/:id",
  authMiddleware.checkJWTToken,
  paymentController.updateMigrationPayment,
);

router.get(
  "/migration/:id",
  authMiddleware.checkJWTToken,
  paymentController.getMigrationPayment,
);

module.exports = router;
```

## Testing Protected Routes

Use supertest to test authentication:

```javascript
// tests/integration/routes/oauthRoutes.test.js
const request = require("supertest");
const app = require("../../../src/interfaces/http/server");
const jwt = require("jsonwebtoken");
const config = require("../../../src/infrastructure/config");

describe("OAuth Routes", () => {
  let authToken;
  let userId;

  beforeAll(async () => {
    // Create test user
    const user = await UserFactory.create({ role: "admin" });
    userId = user._id;

    // Generate valid JWT token
    authToken = jwt.sign({ id: userId }, config.jwtSecret, { expiresIn: "1h" });
  });

  describe("POST /oauth/klaviyo/connect", () => {
    it("should return 401 without token", async () => {
      const response = await request(app)
        .post("/api/v1/oauth/klaviyo/connect")
        .send({ redirectUri: "http://localhost:3000/callback" });

      expect(response.status).toBe(401);
      expect(response.body.message).toContain("No token provided");
    });

    it("should return 401 with invalid token", async () => {
      const response = await request(app)
        .post("/api/v1/oauth/klaviyo/connect")
        .set("Authorization", "Bearer invalid-token")
        .send({ redirectUri: "http://localhost:3000/callback" });

      expect(response.status).toBe(401);
      expect(response.body.message).toContain("Invalid token");
    });

    it("should succeed with valid token", async () => {
      const response = await request(app)
        .post("/api/v1/oauth/klaviyo/connect")
        .set("Authorization", `Bearer ${authToken}`)
        .send({ redirectUri: "http://localhost:3000/callback" });

      expect(response.status).toBe(200);
    });
  });

  describe("GET /oauth/klaviyo/status", () => {
    it("should return user-specific status", async () => {
      const response = await request(app)
        .get("/api/v1/oauth/klaviyo/status")
        .set("Authorization", `Bearer ${authToken}`);

      expect(response.status).toBe(200);
      expect(response.body.data.userId).toBe(userId.toString());
    });
  });
});
```

### Testing Role-Based Access

```javascript
describe("Admin Routes", () => {
  let adminToken;
  let userToken;

  beforeAll(async () => {
    // Create admin user
    const admin = await UserFactory.create({ role: "admin" });
    adminToken = jwt.sign({ id: admin._id }, config.jwtSecret, {
      expiresIn: "1h",
    });

    // Create regular user
    const user = await UserFactory.create({ role: "user" });
    userToken = jwt.sign({ id: user._id }, config.jwtSecret, {
      expiresIn: "1h",
    });
  });

  describe("GET /admin/workflows", () => {
    it("should return 403 for non-admin user", async () => {
      const response = await request(app)
        .get("/api/v1/admin/workflows")
        .set("Authorization", `Bearer ${userToken}`);

      expect(response.status).toBe(403);
      expect(response.body.message).toContain("Unauthorized");
    });

    it("should succeed for admin user", async () => {
      const response = await request(app)
        .get("/api/v1/admin/workflows")
        .set("Authorization", `Bearer ${adminToken}`);

      expect(response.status).toBe(200);
    });
  });
});
```

## Best Practices

1. **Always Use checkJWTToken First**: Authentication before authorization

   ```javascript
   // Correct
   router.use(
     authMiddleware.checkJWTToken,
     authMiddleware.checkRole(ROLES.ADMIN),
   );

   // Wrong - checkRole won't have req.user
   router.use(
     authMiddleware.checkRole(ROLES.ADMIN),
     authMiddleware.checkJWTToken,
   );
   ```

2. **Use router.use() for Route Groups**: Apply middleware once for all routes below

   ```javascript
   // Efficient
   router.use(authMiddleware.checkJWTToken);
   router.get("/route1", handler1);
   router.get("/route2", handler2);

   // Repetitive
   router.get("/route1", authMiddleware.checkJWTToken, handler1);
   router.get("/route2", authMiddleware.checkJWTToken, handler2);
   ```

3. **Order Matters**: Place more restrictive middleware after less restrictive

   ```javascript
   router.use(authMiddleware.checkJWTToken); // All routes authenticated
   router.get("/me", handler); // Any authenticated user
   router.use(authMiddleware.checkRole(ROLES.ADMIN)); // Routes below admin-only
   router.get("/admin-only", handler); // Admin only
   ```

4. **Use checkAnyRoles for OR Logic**: When multiple roles should have access

   ```javascript
   // Correct - admin OR super_admin
   router.use(authMiddleware.checkAnyRoles([ROLES.ADMIN, ROLES.SUPER_ADMIN]));

   // Wrong - requires BOTH roles (impossible)
   router.use(
     authMiddleware.checkRole(ROLES.ADMIN),
     authMiddleware.checkRole(ROLES.SUPER_ADMIN),
   );
   ```

5. **Prefer 403 Over 401 for Authorization**: Use correct HTTP status codes
   - **401 Unauthorized**: Authentication failed (no token, invalid token, expired token)
   - **403 Forbidden**: Authenticated but insufficient permissions (role check failed)

6. **Never Trust Client-Provided User Info**: Always use `req.user` from middleware

   ```javascript
   // Correct - use authenticated user from middleware
   const userId = req.user._id;

   // Wrong - client can fake this
   const userId = req.body.userId;
   ```

7. **Handle Token Expiration Gracefully**: Frontend should refresh tokens before expiry
   - Backend returns 401 with "Token expired" message
   - Frontend refreshes token and retries request

8. **Test Authentication Thoroughly**: Test missing token, invalid token, expired token, and insufficient permissions

## Common Pitfalls

1. **Forgetting to Call next()**: Middleware won't proceed to next handler

   ```javascript
   // Wrong - hangs forever
   const checkRole = (role) => {
     return (req, res, next) => {
       if (!hasRole) {
         next(new ApplicationError("Unauthorized", 403));
       }
       // Missing next() here!
     };
   };

   // Correct
   const checkRole = (role) => {
     return (req, res, next) => {
       if (!hasRole) {
         return next(new ApplicationError("Unauthorized", 403));
       }
       next();
     };
   };
   ```

2. **Using checkRole Before checkJWTToken**: `req.user` won't exist yet
3. **Not Returning After Calling next(error)**: Code continues executing

   ```javascript
   // Wrong
   if (error) {
     next(error); // Error passed to handler
     console.log("This still runs!"); // But this executes
   }

   // Correct
   if (error) {
     return next(error); // Early return
   }
   ```

4. **Checking Role String Incorrectly**: Use `role.roleLevel` not `role`
5. **Not Handling TokenExpiredError**: Clients need clear feedback to refresh
6. **Protecting Callback Routes**: OAuth callbacks should NOT require authentication

## Related Files

- `src/interfaces/http/middlewares/auth.js` - Authentication middleware
- `src/constants/index.js` - Role constants
- `src/infrastructure/repositories/userRepository.js` - User/role lookup
- `src/infrastructure/config/index.js` - JWT secret configuration
- `src/interfaces/http/middlewares/errorHandler.js` - Error handling

## References

- [JWT.io](https://jwt.io/) - JWT token format and libraries
- [Express Middleware Guide](https://expressjs.com/en/guide/writing-middleware.html)
- [HTTP Status Codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)
