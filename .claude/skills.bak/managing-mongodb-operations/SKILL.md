---
name: managing-mongodb-operations
description: Query optimization, indexing strategies, aggregation pipelines, and schema migrations for MongoDB. Covers common patterns for Users, Workflows, OAuthConnections, and WorkflowExecutions. Use when working with database queries, performance tuning, data migrations, or MongoDB operations.
---

# Managing MongoDB Operations

Optimize and manage MongoDB operations in the Beena Automation Platform backend. This skill covers query patterns, indexing, aggregations, and migrations for the project's data models.

## When to Use This Skill

- Optimizing slow database queries
- Creating or modifying indexes
- Writing aggregation pipelines for analytics
- Migrating or transforming existing data
- Debugging MongoDB connection issues
- Understanding the project's data models

## Database Architecture Overview

### Project Structure

```
automation-webapp-be/
├── src/
│   └── infrastructure/
│       ├── database/mongodb/
│       │   ├── connection.js           # MongoDB connection setup
│       │   ├── models/
│       │   │   ├── User.js             # User accounts
│       │   │   ├── BaseWorkflow.js     # Workflow templates
│       │   │   ├── UserWorkflow.js     # User-specific workflows
│       │   │   ├── WorkflowExecution.js # Execution history
│       │   │   ├── OAuthConnection.js  # OAuth tokens (encrypted)
│       │   │   └── OAuthState.js       # PKCE state management
│       │   └── seeders/
│       │       └── index.js            # Database seeding
│       └── repositories/
│           ├── userRepository.js
│           └── workflowRepository.js
```

### Environment Configuration

```bash
# .env
MONGODB_URI=mongodb://localhost:27017/beena_extension
MONGODB_OPTIONS=retryWrites=true &
w=majority

# Production (with auth)
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/beena_extension
```

## Core Data Models

### User Model

```javascript
// Key fields and their purposes
const userSchema = {
  email: String, // Unique, indexed
  name: String,
  role: String, // 'admin' | 'user' | 'worker'
  googleId: String, // OAuth identifier
  avatar: String,
  lastLogin: Date,
  preferences: Object,
  createdAt: Date,
  updatedAt: Date,
};

// Important indexes
userSchema.index({ email: 1 }, { unique: true });
userSchema.index({ googleId: 1 }, { sparse: true });
userSchema.index({ role: 1 });
```

### WorkflowExecution Model

```javascript
const executionSchema = {
  workflowId: ObjectId, // Reference to UserWorkflow
  userId: ObjectId, // Who initiated
  status: String, // 'pending' | 'running' | 'completed' | 'failed'
  paymentIntentId: String, // Stripe payment reference
  startedAt: Date,
  completedAt: Date,
  results: {
    success: Boolean,
    itemsProcessed: Number,
    errors: Array,
  },
  metadata: Object,
};

// Compound indexes for common queries
executionSchema.index({ userId: 1, createdAt: -1 });
executionSchema.index({ status: 1, createdAt: -1 });
executionSchema.index({ workflowId: 1, status: 1 });
```

### OAuthConnection Model

```javascript
const oauthSchema = {
  userId: ObjectId,
  provider: String, // 'klaviyo' | 'mailchimp' | etc.
  accessToken: String, // Encrypted with AES-256
  refreshToken: String, // Encrypted
  expiresAt: Date,
  scope: [String],
  metadata: Object,
};

// Unique compound index
oauthSchema.index({ userId: 1, provider: 1 }, { unique: true });
// Token refresh job index
oauthSchema.index({ expiresAt: 1 });
```

## Common Query Patterns

### 1. Finding Users with OAuth Connections

```javascript
// Get user with their Klaviyo connection
const userWithKlaviyo = await User.aggregate([
  { $match: { _id: userId } },
  {
    $lookup: {
      from: "oauthconnections",
      localField: "_id",
      foreignField: "userId",
      as: "connections",
    },
  },
  {
    $addFields: {
      klaviyoConnection: {
        $first: {
          $filter: {
            input: "$connections",
            cond: { $eq: ["$$this.provider", "klaviyo"] },
          },
        },
      },
    },
  },
  {
    $project: {
      email: 1,
      name: 1,
      hasKlaviyo: { $toBool: "$klaviyoConnection" },
      klaviyoExpiresAt: "$klaviyoConnection.expiresAt",
    },
  },
]);
```

### 2. Workflow Execution Analytics

```javascript
// Get execution statistics for a user
const stats = await WorkflowExecution.aggregate([
  { $match: { userId: new ObjectId(userId) } },
  {
    $group: {
      _id: "$status",
      count: { $sum: 1 },
      avgDuration: {
        $avg: {
          $subtract: ["$completedAt", "$startedAt"],
        },
      },
    },
  },
  {
    $project: {
      status: "$_id",
      count: 1,
      avgDurationMs: { $round: ["$avgDuration", 0] },
    },
  },
]);
```

### 3. Recent Executions with Workflow Details

```javascript
// Get last 10 executions with workflow names
const recentExecutions = await WorkflowExecution.aggregate([
  { $match: { userId: new ObjectId(userId) } },
  { $sort: { createdAt: -1 } },
  { $limit: 10 },
  {
    $lookup: {
      from: "userworkflows",
      localField: "workflowId",
      foreignField: "_id",
      as: "workflow",
    },
  },
  {
    $project: {
      status: 1,
      createdAt: 1,
      completedAt: 1,
      workflowName: { $arrayElemAt: ["$workflow.name", 0] },
      itemsProcessed: "$results.itemsProcessed",
    },
  },
]);
```

### 4. Token Refresh Query (Used by Cron Job)

```javascript
// Find tokens expiring in next 10 minutes
const expiringTokens = await OAuthConnection.find({
  expiresAt: {
    $lt: new Date(Date.now() + 10 * 60 * 1000),
    $gt: new Date(), // Not already expired
  },
}).populate("userId", "email name");
```

## Indexing Strategies

### Creating Effective Indexes

```javascript
// Compound index for filtering + sorting
// Order matters: equality → sort → range
workflowExecutionSchema.index(
  { userId: 1, status: 1, createdAt: -1 },
  { name: "user_status_date" },
);

// Partial index (only index documents matching condition)
userSchema.index(
  { lastLogin: 1 },
  {
    name: "active_users",
    partialFilterExpression: {
      lastLogin: { $gt: new Date("2024-01-01") },
    },
  },
);

// Text index for search
baseWorkflowSchema.index(
  { name: "text", description: "text" },
  { name: "workflow_search" },
);

// TTL index for auto-deletion (OAuth states expire after 10 minutes)
oauthStateSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });
```

### Analyzing Index Usage

```javascript
// Check which indexes are being used
const explanation = await WorkflowExecution.find({
  userId: userId,
  status: "completed",
})
  .sort({ createdAt: -1 })
  .explain("executionStats");

console.log("Index used:", explanation.queryPlanner.winningPlan.inputStage);
console.log("Docs examined:", explanation.executionStats.totalDocsExamined);
console.log("Docs returned:", explanation.executionStats.nReturned);
```

### Index Guidelines

| Query Pattern           | Recommended Index                      |
| ----------------------- | -------------------------------------- |
| Find by single field    | Single field index                     |
| Find by multiple fields | Compound index (equality fields first) |
| Find + Sort             | Compound index (filter + sort fields)  |
| Range queries           | Put range field last in compound       |
| Text search             | Text index                             |
| Auto-expire documents   | TTL index                              |

## Migration Scripts

### Migration Template

**src/infrastructure/database/mongodb/migrations/migrate_template.js**:

```javascript
const mongoose = require("mongoose");
const config = require("../../config");
const logger = require("../../logging/logger");

async function migrate() {
  try {
    // Connect to database
    await mongoose.connect(config.mongodb.uri, config.mongodb.options);
    logger.info("Connected to MongoDB");

    // Your migration logic here
    const result = await performMigration();

    logger.info("Migration completed", result);
  } catch (error) {
    logger.error("Migration failed", error);
    process.exit(1);
  } finally {
    await mongoose.connection.close();
  }
}

async function performMigration() {
  // Example: Add new field to all documents
  const result = await mongoose.connection.db
    .collection("users")
    .updateMany(
      { newField: { $exists: false } },
      { $set: { newField: "defaultValue" } },
    );

  return {
    matched: result.matchedCount,
    modified: result.modifiedCount,
  };
}

migrate();
```

### Common Migration Patterns

#### Adding a New Field

```javascript
// Add 'preferences' field to existing users
await User.updateMany(
  { preferences: { $exists: false } },
  {
    $set: {
      preferences: {
        notifications: true,
        theme: "light",
      },
    },
  },
);
```

#### Renaming a Field

```javascript
// Rename 'userName' to 'name'
await User.updateMany({}, { $rename: { userName: "name" } });
```

#### Data Transformation

```javascript
// Convert string dates to Date objects
const docs = await Collection.find({ createdAt: { $type: "string" } });

for (const doc of docs) {
  await Collection.updateOne(
    { _id: doc._id },
    { $set: { createdAt: new Date(doc.createdAt) } },
  );
}
```

#### Backfill from Related Collection

```javascript
// Add email to executions from user
const executions = await WorkflowExecution.find({
  userEmail: { $exists: false },
});

for (const exec of executions) {
  const user = await User.findById(exec.userId, "email");
  if (user) {
    await WorkflowExecution.updateOne(
      { _id: exec._id },
      { $set: { userEmail: user.email } },
    );
  }
}
```

## Performance Optimization

### Query Optimization Tips

```javascript
// BAD: Fetching entire documents when only ID needed
const users = await User.find({ role: "admin" });
const userIds = users.map((u) => u._id);

// GOOD: Projection to fetch only required fields
const userIds = await User.find({ role: "admin" }).distinct("_id");

// BAD: Multiple queries in loop
for (const id of ids) {
  const user = await User.findById(id);
}

// GOOD: Single query with $in
const users = await User.find({ _id: { $in: ids } });

// BAD: Count with find().length
const count = (await User.find({ role: "user" })).length;

// GOOD: Use countDocuments
const count = await User.countDocuments({ role: "user" });

// GOOD: Use estimatedDocumentCount for total (faster)
const total = await User.estimatedDocumentCount();
```

### Pagination Pattern

```javascript
// Cursor-based pagination (better for large datasets)
async function getExecutionsCursor(userId, lastId, limit = 20) {
  const query = { userId: new ObjectId(userId) };

  if (lastId) {
    query._id = { $lt: new ObjectId(lastId) };
  }

  return WorkflowExecution.find(query).sort({ _id: -1 }).limit(limit).lean(); // Use lean() for read-only queries
}

// Offset-based pagination (simpler but slower for large offsets)
async function getExecutionsOffset(userId, page = 1, limit = 20) {
  const skip = (page - 1) * limit;

  const [executions, total] = await Promise.all([
    WorkflowExecution.find({ userId })
      .sort({ createdAt: -1 })
      .skip(skip)
      .limit(limit)
      .lean(),
    WorkflowExecution.countDocuments({ userId }),
  ]);

  return {
    data: executions,
    pagination: {
      page,
      limit,
      total,
      pages: Math.ceil(total / limit),
    },
  };
}
```

### Bulk Operations

```javascript
// Efficient bulk writes
const bulkOps = items.map((item) => ({
  updateOne: {
    filter: { _id: item._id },
    update: { $set: { status: item.newStatus } },
  },
}));

const result = await WorkflowExecution.bulkWrite(bulkOps, {
  ordered: false, // Continue on error
});

console.log({
  matched: result.matchedCount,
  modified: result.modifiedCount,
  errors: result.getWriteErrors(),
});
```

## Connection Management

### Connection Setup

**src/infrastructure/database/mongodb/connection.js**:

```javascript
const mongoose = require("mongoose");
const config = require("../../config");
const logger = require("../../logging/logger");

const connectionOptions = {
  maxPoolSize: 10,
  minPoolSize: 2,
  serverSelectionTimeoutMS: 5000,
  socketTimeoutMS: 45000,
  family: 4, // Use IPv4
};

async function connect() {
  try {
    await mongoose.connect(config.mongodb.uri, connectionOptions);
    logger.info("MongoDB connected successfully");

    mongoose.connection.on("error", (err) => {
      logger.error("MongoDB connection error:", err);
    });

    mongoose.connection.on("disconnected", () => {
      logger.warn("MongoDB disconnected");
    });

    // Graceful shutdown
    process.on("SIGINT", async () => {
      await mongoose.connection.close();
      logger.info("MongoDB connection closed due to app termination");
      process.exit(0);
    });
  } catch (error) {
    logger.error("MongoDB connection failed:", error);
    process.exit(1);
  }
}

module.exports = { connect };
```

## Debugging MongoDB Issues

### Common Issues and Solutions

| Issue               | Diagnostic                       | Solution                       |
| ------------------- | -------------------------------- | ------------------------------ |
| Slow queries        | Check with `.explain()`          | Add appropriate indexes        |
| Connection timeouts | Check `serverSelectionTimeoutMS` | Verify network/firewall        |
| Memory issues       | Check `db.serverStatus().mem`    | Add more RAM, optimize queries |
| Lock contention     | Check `db.currentOp()`           | Reduce long-running operations |
| Duplicate key error | Check unique indexes             | Handle upsert properly         |

### Useful Diagnostic Commands

```javascript
// Check current operations
db.currentOp({ secs_running: { $gt: 5 } });

// Check index usage stats
db.collection.aggregate([{ $indexStats: {} }]);

// Check collection stats
db.collection.stats();

// Profile slow queries (>100ms)
db.setProfilingLevel(1, { slowms: 100 });
db.system.profile.find().sort({ ts: -1 }).limit(10);
```

## Best Practices

1. **Always use indexes** for frequently queried fields
2. **Use `.lean()`** for read-only queries (skips Mongoose overhead)
3. **Limit projection** to only needed fields
4. **Use cursor-based pagination** for large datasets
5. **Avoid `$where`** and JavaScript execution in queries
6. **Use compound indexes** for multi-field queries
7. **Monitor slow queries** with profiling
8. **Handle connection errors** gracefully
9. **Use transactions** for multi-document operations
10. **Test migrations** on a copy of production data
