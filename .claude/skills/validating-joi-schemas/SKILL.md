# validating-joi-schemas

## Description

Implement Joi validation schemas for the Node.js/Express backend following the project's established patterns. Covers schema definition, custom validators, error messages, middleware integration, and common validation patterns for authentication, workflows, and user input.

## When to Use

- Adding new API endpoints that accept request data (body, params, query)
- Implementing input validation for authentication flows
- Creating validation for workflow or automation payloads
- Customizing error messages for better user feedback
- Defining reusable validation schemas across controllers
- Implementing complex validation logic (password rules, conditional validation)

## Prerequisites

- Basic understanding of Joi validation library
- Familiarity with Express.js middleware patterns
- Knowledge of the backend's Clean Architecture structure (`src/application/joiValidations/`)

## Key Concepts

### Schema Organization

Validation schemas are organized by domain in `src/application/joiValidations/schemas/`:

```
src/application/joiValidations/
├── validateRequest.js          # Central validation function
├── schemas/
│   ├── authSchema.js           # Authentication (login, register, password reset)
│   ├── userSchema.js           # User management
│   ├── workflowValidations.js  # Workflow CRUD operations
│   ├── paymentSchema.js        # Payment operations
│   ├── adminSchema.js          # Admin-specific operations
│   └── workerSchema.js         # Worker-specific operations
```

### Central Validation Function

The `validateRequest.js` module provides a unified validation interface:

```javascript
// src/application/joiValidations/validateRequest.js
const httpStatus = require("http-status");
const {
  ApplicationError,
} = require("../../interfaces/http/middlewares/errorHandler");

/**
 * Validates data against the provided schema
 * @param {Object} data - Data to validate
 * @param {Joi.Schema} schema - Joi schema for validation
 * @returns {Object} Validated and sanitized data
 * @throws {ApplicationError} If validation fails
 */
const validateRequest = (data, schema) => {
  const { error, value } = schema.validate(data, {
    abortEarly: false, // Collect all errors, not just the first
    stripUnknown: true, // Remove fields not defined in schema
  });

  if (error) {
    throw new ApplicationError(
      error.details.map((detail) => detail.message).join(", "),
      httpStatus.BAD_REQUEST,
    );
  }

  return value; // Returns sanitized data
};

module.exports = validateRequest;
```

**Key Options**:

- `abortEarly: false` - Returns all validation errors at once for better UX
- `stripUnknown: true` - Removes unknown fields, preventing injection attacks

## Implementation Patterns

### 1. Basic Schema Definition

Define schemas with custom error messages for better user feedback:

```javascript
// src/application/joiValidations/schemas/authSchema.js
const Joi = require("joi");

const loginSchema = Joi.object({
  email: Joi.string().email().required().messages({
    "string.email": "Please provide a valid email address",
    "any.required": "Email is required",
  }),
  password: Joi.string().required().messages({
    "any.required": "Password is required",
  }),
});

module.exports = { loginSchema };
```

### 2. Custom Validators

Use `.custom()` for complex validation logic:

```javascript
const registerSchema = Joi.object({
  email: Joi.string().email().required().messages({
    "string.email": "Please provide a valid email address",
    "any.required": "Email is required",
  }),
  password: Joi.string()
    .required()
    .min(8)
    .custom((value, helpers) => {
      if (!/[a-z]/.test(value)) {
        return helpers.message(
          "Password must contain at least one lowercase letter",
        );
      }
      if (!/[A-Z]/.test(value)) {
        return helpers.message(
          "Password must contain at least one uppercase letter",
        );
      }
      if (!/\d/.test(value)) {
        return helpers.message("Password must contain at least one number");
      }
      if (!/[@$!%*?&]/.test(value)) {
        return helpers.message(
          "Password must contain at least one special character (@$!%*?&)",
        );
      }
      return value;
    })
    .messages({
      "string.min": "Password must be at least 8 characters long",
      "any.required": "Password is required",
    }),
});
```

**Alternative**: Use `.pattern()` with regex for simpler cases:

```javascript
password: Joi.string()
  .min(8)
  .required()
  .pattern(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/)
  .messages({
    'string.min': 'Password must be at least 8 characters long',
    'string.pattern.base': 'Password must contain at least one uppercase letter, one lowercase letter, one number and one special character',
    'any.required': 'Password is required',
  }),
```

### 3. Reference Validation

Validate one field against another using `Joi.ref()`:

```javascript
const completeUserSetupSchema = Joi.object({
  password: Joi.string().required().min(8).messages({
    "string.min": "Password must be at least 8 characters long",
    "any.required": "Password is required",
  }),
  confirmPassword: Joi.string().required().valid(Joi.ref("password")).messages({
    "any.only": "Passwords do not match",
    "any.required": "Password confirmation is required",
  }),
});
```

### 4. Optional Fields and Defaults

Handle optional fields and default values:

```javascript
const userFilterSchema = Joi.object({
  name: Joi.string().optional().messages({
    "string.base": "Name filter must be a string",
  }),
  page: Joi.number().integer().min(1).default(1).messages({
    "number.base": "Page must be a number",
    "number.min": "Page must be at least 1",
  }),
  limit: Joi.number().integer().min(1).max(100).default(10).messages({
    "number.max": "Limit cannot exceed 100",
  }),
}).unknown(true); // Allow additional query parameters
```

### 5. Stripping Internal Fields

Remove fields that should be set internally, not by the client:

```javascript
const createWorkflowPayload = Joi.object()
  .keys({
    name: Joi.string().required(),
    actions: Joi.array().required(),
    // Strip internal fields
    _id: Joi.any().strip(),
    id: Joi.any().strip(),
    userId: Joi.any().strip(), // Set from authenticated user
    createdAt: Joi.any().strip(),
    created_at: Joi.any().strip(),
    updatedAt: Joi.any().strip(),
    updated_at: Joi.any().strip(),
    __v: Joi.any().strip(), // Mongoose version key
  })
  .unknown(true);
```

### 6. Update Schema Pattern

For PATCH endpoints, require at least one field:

```javascript
const updateUserSchema = Joi.object({
  email: Joi.string().email().messages({
    "string.email": "Please provide a valid email address",
  }),
  password: Joi.string().min(8).messages({
    "string.min": "Password must be at least 8 characters long",
  }),
})
  .min(1)
  .messages({
    "object.min": "At least one field must be provided for update",
  });
```

### 7. Integration with Controllers

Use validation in controller methods:

```javascript
// src/interfaces/http/controllers/authController.js
const validateRequest = require("../../../application/joiValidations/validateRequest");
const {
  loginSchema,
  registerSchema,
} = require("../../../application/joiValidations/schemas/authSchema");

class AuthController {
  async register(req, res, next) {
    try {
      // Validate request body
      const validatedData = validateRequest(req.body, registerSchema);

      // Use validated data (strips unknown fields, applies defaults)
      const registeredUser =
        await this.registerUserUseCase.execute(validatedData);

      res.status(httpStatus.CREATED).json({
        status: "success",
        data: { user: registeredUser },
      });
    } catch (error) {
      next(error); // ApplicationError caught by global error handler
    }
  }

  async login(req, res, next) {
    try {
      validateRequest(req.body, loginSchema);

      const { email, password } = req.body;
      const result = await this.loginUserUseCase.execute({ email, password });

      res.status(httpStatus.OK).json({
        status: "success",
        data: result,
      });
    } catch (error) {
      next(error);
    }
  }
}
```

### 8. Array Validation

Validate arrays with nested object schemas:

```javascript
const workflowExecutionSchema = Joi.object({
  workflowId: Joi.string().required(),
  actions: Joi.array()
    .items(
      Joi.object({
        type: Joi.string()
          .required()
          .valid("click", "type", "navigate", "wait"),
        selector: Joi.string().when("type", {
          is: Joi.valid("click", "type"),
          then: Joi.required(),
          otherwise: Joi.optional(),
        }),
        value: Joi.string().when("type", {
          is: "type",
          then: Joi.required(),
          otherwise: Joi.optional(),
        }),
        timeout: Joi.number().integer().min(0).default(30000),
      }),
    )
    .min(1)
    .required()
    .messages({
      "array.min": "At least one action is required",
    }),
});
```

### 9. Conditional Validation

Use `.when()` for conditional validation:

```javascript
const actionSchema = Joi.object({
  type: Joi.string().required().valid("click", "type", "navigate"),
  selector: Joi.string().when("type", {
    is: Joi.valid("click", "type"),
    then: Joi.required(),
    otherwise: Joi.forbidden(),
  }),
  value: Joi.string().when("type", {
    is: "type",
    then: Joi.required(),
    otherwise: Joi.forbidden(),
  }),
  url: Joi.string().uri().when("type", {
    is: "navigate",
    then: Joi.required(),
    otherwise: Joi.forbidden(),
  }),
});
```

### 10. Global Schema Messages

Set custom messages at the schema level:

```javascript
const schema = Joi.object({
  email: Joi.string().email().required(),
  password: Joi.string().required(),
}).messages({
  "object.unknown": "Invalid field(s) in request",
  "any.required": "{#label} is a required field",
});
```

## Common Validation Patterns

### Email Validation

```javascript
email: Joi.string().email().required().messages({
  "string.email": "Please provide a valid email address",
  "any.required": "Email is required",
});
```

### Password Validation (Complex)

```javascript
password: Joi.string()
  .required()
  .min(8)
  .custom((value, helpers) => {
    if (!/[a-z]/.test(value)) {
      return helpers.message(
        "Password must contain at least one lowercase letter",
      );
    }
    if (!/[A-Z]/.test(value)) {
      return helpers.message(
        "Password must contain at least one uppercase letter",
      );
    }
    if (!/\d/.test(value)) {
      return helpers.message("Password must contain at least one number");
    }
    if (!/[@$!%*?&]/.test(value)) {
      return helpers.message(
        "Password must contain at least one special character (@$!%*?&)",
      );
    }
    return value;
  });
```

### MongoDB ObjectId Validation

```javascript
userId: Joi.string()
  .pattern(/^[0-9a-fA-F]{24}$/)
  .required()
  .messages({
    "string.pattern.base": "Invalid user ID format",
  });
```

### URL Validation

```javascript
webhookUrl: Joi.string().uri().optional().allow("").messages({
  "string.uri": "Please provide a valid URL",
});
```

### Enum Validation

```javascript
role: Joi.string().valid("admin", "user", "worker").required().messages({
  "any.only": "Role must be one of: admin, user, worker",
});
```

### Date Validation

```javascript
startDate: Joi.date().iso().required().messages({
  'date.format': 'Start date must be in ISO 8601 format',
}),
endDate: Joi.date().iso().min(Joi.ref('startDate')).messages({
  'date.min': 'End date must be after start date',
})
```

## Error Handling

Validation errors are automatically converted to `ApplicationError` with status 400:

```javascript
// Error response structure
{
  "status": "error",
  "message": "Email is required, Password must be at least 8 characters long",
  "statusCode": 400
}
```

The global error handler in `src/interfaces/http/middlewares/errorHandler.js` catches these errors and formats them for the client.

## Testing Validation

Test validation logic in unit tests:

```javascript
// tests/unit/validation/authSchema.test.js
const Joi = require("joi");
const {
  loginSchema,
  registerSchema,
} = require("../../../src/application/joiValidations/schemas/authSchema");

describe("Auth Validation Schemas", () => {
  describe("loginSchema", () => {
    it("should validate correct login data", () => {
      const validData = {
        email: "test@example.com",
        password: "password123",
      };

      const { error } = loginSchema.validate(validData);
      expect(error).toBeUndefined();
    });

    it("should fail for invalid email", () => {
      const invalidData = {
        email: "not-an-email",
        password: "password123",
      };

      const { error } = loginSchema.validate(invalidData);
      expect(error).toBeDefined();
      expect(error.details[0].message).toContain("valid email");
    });

    it("should fail for missing password", () => {
      const invalidData = {
        email: "test@example.com",
      };

      const { error } = loginSchema.validate(invalidData);
      expect(error).toBeDefined();
      expect(error.details[0].message).toContain("Password is required");
    });
  });

  describe("registerSchema", () => {
    it("should validate strong password", () => {
      const validData = {
        fullName: "Test User",
        email: "test@example.com",
        password: "StrongPass123!",
      };

      const { error } = registerSchema.validate(validData);
      expect(error).toBeUndefined();
    });

    it("should fail for weak password", () => {
      const invalidData = {
        fullName: "Test User",
        email: "test@example.com",
        password: "weak",
      };

      const { error } = registerSchema.validate(invalidData);
      expect(error).toBeDefined();
    });
  });
});
```

## Best Practices

1. **Custom Messages**: Always provide user-friendly error messages
2. **Centralized Validation**: Use `validateRequest()` for consistency
3. **Strip Internal Fields**: Remove fields like `_id`, `createdAt` that should be set server-side
4. **Fail Fast**: Use `abortEarly: false` to return all errors at once
5. **Security**: Use `stripUnknown: true` to prevent injection of unexpected fields
6. **Defaults**: Set sensible defaults for optional fields (e.g., pagination)
7. **Conditional Validation**: Use `.when()` for complex dependencies
8. **Test Thoroughly**: Write unit tests for validation logic
9. **Reusable Schemas**: Extract common patterns (email, password) into reusable components
10. **Document Schemas**: Add JSDoc comments explaining validation rules

## Common Pitfalls

1. **Forgetting `stripUnknown`**: Without this, clients can inject unexpected fields
2. **Not Using `.strip()`**: Internal fields can be overwritten if not stripped
3. **Generic Error Messages**: Users need clear feedback about what's wrong
4. **Missing `.min(1)` on Updates**: PATCH endpoints should require at least one field
5. **Not Testing Edge Cases**: Test missing fields, invalid formats, boundary conditions
6. **Overusing `.unknown(true)`**: Only allow unknown fields when truly needed (e.g., filters)
7. **Circular References**: Be careful with `Joi.ref()` to avoid infinite loops
8. **Not Validating Arrays**: Always validate array items, not just the array itself

## Related Files

- `src/application/joiValidations/validateRequest.js` - Central validation function
- `src/application/joiValidations/schemas/` - All validation schemas
- `src/interfaces/http/middlewares/errorHandler.js` - Error handling middleware
- `src/interfaces/http/controllers/` - Controllers using validation

## References

- [Joi Documentation](https://joi.dev/api/)
- [Joi Custom Validators](https://joi.dev/api/?v=17.6.0#anycustommethod-description)
- [Joi Conditional Validation](https://joi.dev/api/?v=17.6.0#anywhenref-options)
