---
name: creating-mongoose-schemas
description: Design MongoDB schemas with Mongoose for the automation backend. Covers schema types, indexes, virtuals, middleware hooks, and relationships. Use when adding new data entities, optimizing queries, or modifying existing schemas.
---

# Creating Mongoose Schemas

Design and implement MongoDB schemas using Mongoose for the automation workflow backend. Focus on proper indexing, relationships, and schema patterns specific to the project.

## When to Use This Skill

- Adding new data models/collections
- Modifying existing schemas
- Optimizing database queries with indexes
- Implementing data relationships
- Adding schema middleware (pre/post hooks)
- Troubleshooting schema-related issues

## Schema Basics

### Project Schema Structure

**Location**: `src/infrastructure/database/mongodb/models/`

```javascript
const mongoose = require("mongoose");

const schemaName = new mongoose.Schema(
  {
    // Field definitions
  },
  {
    timestamps: true, // Adds createdAt, updatedAt
    collection: "collection_name", // Optional: custom collection name
  },
);

module.exports = mongoose.model("ModelName", schemaName);
```

## Core Field Types

### Common Types

```javascript
const workflowSchema = new mongoose.Schema({
  // String
  name: {
    type: String,
    required: [true, "Name is required"],
    trim: true,
    maxlength: [100, "Name cannot exceed 100 characters"],
    minlength: [3, "Name must be at least 3 characters"],
  },

  // Number
  priority: {
    type: Number,
    default: 0,
    min: [0, "Priority must be positive"],
    max: [10, "Priority cannot exceed 10"],
  },

  // Boolean
  isActive: {
    type: Boolean,
    default: true,
    index: true, // Add index for filtered queries
  },

  // Date
  scheduledAt: {
    type: Date,
    default: Date.now,
    index: true,
  },

  // Array of Strings
  tags: {
    type: [String],
    default: [],
  },

  // Enum
  status: {
    type: String,
    enum: {
      values: ["draft", "active", "paused", "completed"],
      message: "{VALUE} is not a valid status",
    },
    default: "draft",
    index: true, // Frequently filtered
  },

  // Mixed/Any type
  metadata: {
    type: mongoose.Schema.Types.Mixed,
    default: {},
  },
});
```

### ObjectId References

```javascript
const workflowSchema = new mongoose.Schema({
  userId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: "User", // Reference to User model
    required: true,
    index: true, // Index for user-scoped queries
  },

  // Array of references
  tags: [
    {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Tag",
    },
  ],
});
```

## Indexing Strategies

### Single Field Indexes

```javascript
const userSchema = new mongoose.Schema({
  email: {
    type: String,
    required: true,
    unique: true, // Creates unique index
    index: true, // Creates regular index (redundant with unique)
    lowercase: true, // Normalize before saving
  },

  role: {
    type: String,
    enum: ["admin", "user", "worker"],
    index: true, // Frequently filtered
  },

  lastLogin: {
    type: Date,
    index: true, // For sorting/filtering
  },
});
```

### Compound Indexes

```javascript
// Define after schema fields
workflowSchema.index({ userId: 1, status: 1 }); // User's workflows by status
workflowSchema.index({ userId: 1, createdAt: -1 }); // User's recent workflows
workflowSchema.index({ isActive: 1, scheduledAt: 1 }); // Active scheduled workflows
```

**1 = ascending, -1 = descending**

### Text Indexes (Search)

```javascript
workflowSchema.index(
  {
    name: "text",
    description: "text",
  },
  {
    weights: {
      name: 10, // Name matches more important
      description: 5,
    },
  },
);
```

### TTL Indexes (Auto-delete)

```javascript
const oauthStateSchema = new mongoose.Schema({
  state: String,
  expiresAt: {
    type: Date,
    required: true,
    index: true,
  },
});

// Auto-delete documents after expiresAt
oauthStateSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });
```

## Schema Middleware (Hooks)

### Pre-save Hooks

```javascript
const userSchema = new mongoose.Schema({
  email: String,
  password: String,
});

// Hash password before saving
userSchema.pre("save", async function (next) {
  // Only hash if password is modified
  if (!this.isModified("password")) {
    return next();
  }

  const bcrypt = require("bcryptjs");
  this.password = await bcrypt.hash(this.password, 10);
  next();
});
```

### Post-save Hooks

```javascript
workflowSchema.post("save", async function (doc) {
  // Log creation
  console.log(`Workflow ${doc._id} saved`);

  // Trigger side effects (notifications, etc.)
  // Note: Don't use arrow functions, need 'this' context
});
```

### Pre-remove Hooks

```javascript
userSchema.pre("remove", async function (next) {
  // Clean up user's workflows before deleting user
  await mongoose.model("Workflow").deleteMany({ userId: this._id });
  next();
});
```

## Virtual Fields

### Computed Properties

```javascript
const userSchema = new mongoose.Schema({
  firstName: String,
  lastName: String,
});

// Virtual field (not stored in DB)
userSchema.virtual("fullName").get(function () {
  return `${this.firstName} ${this.lastName}`;
});

// Include virtuals in JSON/Object output
userSchema.set("toJSON", { virtuals: true });
userSchema.set("toObject", { virtuals: true });
```

### Virtual Populate

```javascript
const userSchema = new mongoose.Schema({
  email: String,
});

// Virtual populate (not stored, populated on demand)
userSchema.virtual("workflows", {
  ref: "Workflow",
  localField: "_id",
  foreignField: "userId",
});
```

## Schema Methods

### Instance Methods

```javascript
userSchema.methods.comparePassword = async function (candidatePassword) {
  const bcrypt = require("bcryptjs");
  return bcrypt.compare(candidatePassword, this.password);
};

// Usage:
// const user = await User.findOne({ email });
// const isMatch = await user.comparePassword(password);
```

### Static Methods

```javascript
userSchema.statics.findByEmail = function (email) {
  return this.findOne({ email: email.toLowerCase() });
};

// Usage:
// const user = await User.findByEmail('test@example.com');
```

## Relationships

### One-to-Many (Embedded)

```javascript
const workflowSchema = new mongoose.Schema({
  name: String,
  steps: [
    {
      type: {
        type: String,
        required: true,
      },
      action: String,
      params: mongoose.Schema.Types.Mixed,
    },
  ],
});
```

**Use When**: Few items, always accessed together, won't grow unbounded

### One-to-Many (Referenced)

```javascript
const workflowSchema = new mongoose.Schema({
  userId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: "User",
    required: true,
  },
});

// Query with population
const workflow = await Workflow.findById(id).populate("userId");
```

**Use When**: Many items, accessed independently, may grow large

### Many-to-Many

```javascript
const workflowSchema = new mongoose.Schema({
  tags: [
    {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Tag",
    },
  ],
});

const tagSchema = new mongoose.Schema({
  name: String,
  workflows: [
    {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Workflow",
    },
  ],
});
```

## Project-Specific Schemas

### User Schema

```javascript
const userSchema = new mongoose.Schema(
  {
    email: {
      type: String,
      required: true,
      unique: true,
      lowercase: true,
      trim: true,
      index: true,
    },
    password: {
      type: String,
      required: true,
      select: false, // Exclude from queries by default
    },
    role: {
      type: String,
      enum: ["admin", "user", "worker"],
      default: "user",
      index: true,
    },
    googleId: {
      type: String,
      sparse: true, // Unique but allows nulls
      index: true,
    },
    lastLogin: {
      type: Date,
      default: Date.now,
    },
  },
  {
    timestamps: true,
  },
);

// Indexes
userSchema.index({ email: 1 }, { unique: true });
userSchema.index({ role: 1, lastLogin: -1 });

module.exports = mongoose.model("User", userSchema);
```

### Workflow Schema

```javascript
const workflowSchema = new mongoose.Schema(
  {
    name: {
      type: String,
      required: true,
      trim: true,
      maxlength: 200,
    },
    userId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
      required: true,
      index: true,
    },
    status: {
      type: String,
      enum: ["draft", "active", "paused", "completed"],
      default: "draft",
      index: true,
    },
    steps: [
      {
        type: { type: String },
        action: String,
        params: mongoose.Schema.Types.Mixed,
      },
    ],
    lastExecutedAt: {
      type: Date,
      index: true,
    },
    executionCount: {
      type: Number,
      default: 0,
    },
  },
  {
    timestamps: true,
  },
);

// Compound indexes
workflowSchema.index({ userId: 1, status: 1 });
workflowSchema.index({ userId: 1, createdAt: -1 });

module.exports = mongoose.model("Workflow", workflowSchema);
```

### OAuth Connection Schema

```javascript
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
      select: false, // Don't return in queries
    },
    refreshToken: {
      type: String,
      required: true,
      select: false,
    },
    expiresAt: {
      type: Date,
      required: true,
      index: true,
    },
    scope: [String],
    metadata: mongoose.Schema.Types.Mixed,
  },
  {
    timestamps: true,
  },
);

// Unique per user per provider
oauthConnectionSchema.index({ userId: 1, provider: 1 }, { unique: true });

// Find expiring tokens
oauthConnectionSchema.index({ expiresAt: 1 });

module.exports = mongoose.model("OAuthConnection", oauthConnectionSchema);
```

## Schema Options

### Common Options

```javascript
const schema = new mongoose.Schema(
  {
    // fields
  },
  {
    timestamps: true, // Auto createdAt/updatedAt
    collection: "custom_name", // Custom collection name
    toJSON: {
      virtuals: true, // Include virtuals in JSON
      transform: function (doc, ret) {
        delete ret.password; // Remove sensitive fields
        delete ret.__v; // Remove version key
        return ret;
      },
    },
    toObject: { virtuals: true },
  },
);
```

### Validation Messages

```javascript
const schema = new mongoose.Schema({
  email: {
    type: String,
    required: [true, "Email is required"],
    unique: true,
    validate: {
      validator: function (v) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
      },
      message: (props) => `${props.value} is not a valid email`,
    },
  },
});
```

## Query Optimization

### Select Only Needed Fields

```javascript
// Efficient
const user = await User.findById(id).select("email role");

// Inefficient
const user = await User.findById(id); // Returns all fields
```

### Lean Queries (Plain Objects)

```javascript
// Returns plain JavaScript object (faster)
const users = await User.find({}).lean();

// Returns Mongoose document (slower but has methods)
const users = await User.find({});
```

### Population Optimization

```javascript
// Populate specific fields
const workflow = await Workflow.findById(id).populate("userId", "email role"); // Only email and role

// Multiple populations
const workflow = await Workflow.findById(id)
  .populate("userId", "email")
  .populate("tags", "name");
```

## Migration Patterns

### Adding New Field

```javascript
// 1. Add to schema with default
newField: {
  type: String,
  default: 'default_value'
}

// 2. Backfill existing documents (if needed)
await Model.updateMany(
  { newField: { $exists: false } },
  { $set: { newField: 'default_value' } }
);
```

### Removing Field

```javascript
// 1. Remove from schema

// 2. Clean up database
await Model.updateMany({}, { $unset: { oldField: "" } });
```

### Changing Field Type

```javascript
// 1. Add new field with new type
// 2. Migrate data
await Model.find({})
  .cursor()
  .eachAsync(async (doc) => {
    doc.newField = transformOldField(doc.oldField);
    await doc.save();
  });
// 3. Remove old field
// 4. Rename new field (application level) or keep both
```

## Common Patterns

### Soft Delete

```javascript
const schema = new mongoose.Schema({
  isDeleted: {
    type: Boolean,
    default: false,
    index: true,
  },
  deletedAt: Date,
});

schema.methods.softDelete = function () {
  this.isDeleted = true;
  this.deletedAt = new Date();
  return this.save();
};

// Query only non-deleted
const items = await Model.find({ isDeleted: false });
```

### Audit Trail

```javascript
const schema = new mongoose.Schema(
  {
    // ... fields

    createdBy: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
    },
    updatedBy: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User",
    },
  },
  { timestamps: true },
);
```

### Versioning

```javascript
const schema = new mongoose.Schema({
  version: {
    type: Number,
    default: 1,
  },
  // ... other fields
});

schema.pre("save", function (next) {
  if (this.isModified() && !this.isNew) {
    this.version++;
  }
  next();
});
```

## Testing Schemas

```javascript
const mongoose = require("mongoose");
const User = require("./User");

describe("User Schema", () => {
  beforeAll(async () => {
    await mongoose.connect(process.env.TEST_MONGODB_URI);
  });

  afterAll(async () => {
    await mongoose.connection.close();
  });

  it("should hash password before saving", async () => {
    const user = new User({
      email: "test@example.com",
      password: "plaintext",
    });

    await user.save();

    expect(user.password).not.toBe("plaintext");
    expect(user.password.length).toBeGreaterThan(20);
  });

  it("should enforce unique email", async () => {
    const user1 = new User({ email: "test@example.com", password: "pass" });
    await user1.save();

    const user2 = new User({ email: "test@example.com", password: "pass" });
    await expect(user2.save()).rejects.toThrow();
  });
});
```

## Best Practices

1. **Always add indexes** for fields used in queries/filters
2. **Use timestamps** option for automatic createdAt/updatedAt
3. **Validate at schema level** rather than application level
4. **Use enums** for fields with fixed values
5. **Don't over-embed** - balance between embedded and referenced
6. **Use select: false** for sensitive fields
7. **Add defaults** where appropriate
8. **Use lean()** for read-only queries
9. **Index compound queries** (order matters!)
10. **Test migrations** before production

## Next Steps

- See `reference/schema-patterns.md` for advanced patterns
- Check `reference/indexing-guide.md` for optimization strategies
- Review `reference/migration-scripts.md` for data migration examples
