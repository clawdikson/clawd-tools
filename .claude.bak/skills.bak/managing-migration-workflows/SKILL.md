---
name: managing-migration-workflows
description: Manage ESP migration workflows in the React frontend. Covers multi-step flows (Install→Verify→Configure→Complete), job polling, progress tracking, item selection, payment integration, and context management. Use when building migration features or debugging workflow issues.
---

# Managing Migration Workflows

Build and manage ESP data migration workflows for the Beena platform. Focuses on the project's multi-step pattern, job automation, real-time progress tracking, and user-controlled item selection.

## When to Use This Skill

- Creating new migration workflows (Mailchimp→Klaviyo, Yotpo→Klaviyo, etc.)
- Implementing multi-step migration UI flows
- Integrating job polling and progress tracking
- Building item selection interfaces (automations, templates, campaigns)
- Adding payment flows to migration workflows
- Debugging migration step transitions
- Implementing retry logic for failed migrations
- Managing migration context across steps

## Migration Workflow Architecture

### Four-Step Pattern

All migrations follow this structure:

1. **Install** - Install browser extension/native app, verify download
2. **Verify** - Check OAuth connections for source and destination
3. **Configure** - Select items to migrate, initiate migration jobs
4. **Complete** - Show migration results, provide next steps

### Key Components

```
pages/admin/dashboard/migrations/run/
├── index.tsx                           # Main orchestrator
├── hooks/
│   └── useStepAutomation.tsx          # Job automation, polling, progress
├── steps/
│   ├── StepInstall.tsx                # Step 1: App installation
│   ├── StepVerify.tsx                 # Step 2: OAuth verification
│   ├── StepMigration.tsx              # Step 3: Configuration & execution
│   ├── StepComplete.tsx               # Step 4: Results display
│   └── StepMigrationSidebar.tsx       # Live progress sidebar
└── contexts/
    └── MigrationStepContext.tsx       # Shared state across steps
```

## Main Migration Orchestrator

### Basic Structure

```tsx
import React, { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useParams, useNavigate } from "react-router-dom";
import { useMigrationStep } from "@/contexts/MigrationStepContext";
import { getUserWorkflowsById } from "@/shared/services/admins/dashboard";
import { API } from "@/shared/utils/api";

import StepInstall from "./steps/StepInstall";
import StepVerify from "./steps/StepVerify";
import StepConfigure from "./steps/StepMigration";
import StepComplete from "./steps/StepComplete";

const MigrationRunPage: React.FC = () => {
  const { currentStep, setCurrentStep, setMigrationId } = useMigrationStep();
  const { id } = useParams();
  const navigate = useNavigate();
  const [stepMappings, setStepMappings] = useState<Record<string, any>>({});

  // Fetch migration configuration
  const { data: migrationData } = useQuery({
    queryKey: ["migration", id],
    queryFn: () => getUserWorkflowsById(id || ""),
    enabled: !!id,
  });

  // Check OAuth status before allowing migration
  useEffect(() => {
    const checkOAuthAndSetup = async () => {
      if (migrationData?.data) {
        if (migrationData.data.destination?.toLowerCase() === "klaviyo") {
          const response = await API.get("/oauth/klaviyo/status");
          const isConnected = response.data.success && response.data.connected;

          if (!isConnected) {
            message.warning(
              "You need to connect your Klaviyo account first before running this migration.",
              5,
            );
            setTimeout(() => navigate("/integrations"), 1000);
            return;
          }
        }
      }
    };
    checkOAuthAndSetup();
  }, [migrationData?.data, navigate]);

  // Initialize on mount
  useEffect(() => {
    setCurrentStep(0);
    setStepMappings({});
    setMigrationId(id || null);

    // Track migration started
    if (id && migrationData?.data) {
      trackEvent("Migration Started", {
        migration_id: id,
        source_platform: migrationData.data.source || "",
        destination_platform: migrationData.data.destination || "",
      });
    }
  }, [id]);

  // Step definitions
  const steps = [
    {
      title: "Install",
      component: (
        <StepInstall
          stepData={migrationData?.data?.pageContents?.[`step_${currentStep}`]}
          setCurrent={setCurrentStep}
          source={migrationData?.data?.source}
          destination={migrationData?.data?.destination}
        />
      ),
    },
    {
      title: "Verify",
      component: (
        <StepVerify
          stepData={migrationData?.data?.pageContents?.[`step_${currentStep}`]}
          source={migrationData?.data?.source}
          destination={migrationData?.data?.destination}
          setCurrent={setCurrentStep}
          stepMappings={stepMappings}
          setStepMappings={setStepMappings}
        />
      ),
    },
    {
      title: "Configure",
      component: (
        <StepConfigure
          source={migrationData?.data?.source}
          destination={migrationData?.data?.destination}
          baseWorkflowId={migrationData?.data?.baseWorkflowId}
          stepData={migrationData?.data?.pageContents?.[`step_${currentStep}`]}
          setCurrent={setCurrentStep}
          stepMappings={stepMappings}
          setStepMappings={setStepMappings}
        />
      ),
    },
    {
      title: "Complete",
      component: (
        <StepComplete
          stepData={
            migrationData?.data?.pageContents?.[`step_${currentStep - 1}`]
          }
          source={migrationData?.data?.source}
          destination={migrationData?.data?.destination}
          stepMappings={stepMappings}
          selectedItems={stepMappings?.selectedItems}
          progressDetails={stepMappings?.progressDetails}
        />
      ),
    },
  ];

  return (
    <div>
      <h2>
        {migrationData?.data?.pageContents?.[`step_${currentStep}`]?.title}
      </h2>
      <p>
        {migrationData?.data?.pageContents?.[`step_${currentStep}`]?.subtitle}
      </p>
      {steps[currentStep].component}
    </div>
  );
};

export default MigrationRunPage;
```

### Key Patterns

**1. Step Mappings (Shared State)**

```tsx
const [stepMappings, setStepMappings] = useState<Record<string, any>>({});

// Store data from each step for later steps
// Example structure:
{
  StepVerify: {
    fromEmail: "user@mailchimp.com",
    toEmail: "user@klaviyo.com"
  },
  StepConfigure: {
    selectedItems: {
      automations: ["123", "456"],
      templates: ["789"]
    }
  }
}
```

**2. OAuth Gating**

```tsx
// Check OAuth connection before allowing migration
useEffect(() => {
  const checkOAuth = async () => {
    const response = await API.get("/oauth/{provider}/status");
    if (!response.data.connected) {
      message.warning("Connect your account first");
      navigate("/integrations");
    }
  };
  checkOAuth();
}, [migrationData]);
```

**3. Migration Context**

```tsx
const { currentStep, setCurrentStep, setMigrationId } = useMigrationStep();

// Context provides:
// - currentStep: Current step index (0-3)
// - setCurrentStep: Navigate between steps
// - migrationId: Unique identifier for this migration
// - migrationStatuses: Status of each migration item
// - migrationResults: Results from automation jobs
```

## Step Automation Hook

### useStepAutomation Hook

Core hook for job submission, polling, and progress tracking:

```tsx
import { useStepAutomation } from "../hooks/useStepAutomation";

const {
  verifying,
  runAllChecks,
  retryFailedChecks,
  migrationResults,
  completedCount,
  progressDetails,
  actualCompletedItems,
  totalItems,
  currentItem,
} = useStepAutomation({
  steps: migrationSteps,
  stepsCompletedText: "completed",
  onCompleteMessage: "Migration completed successfully!",
  onComplete: () => setCurrent(3), // Move to complete step
  onError: (error) => console.error("Migration error:", error),
  pollInterval: 5000, // Poll every 5 seconds
  stepMappings,
  setStepMappings,
  source: "mailchimp",
  destination: "klaviyo",
  selectedItems: {
    automations: ["123", "456"],
    templates: ["789"],
    campaigns: [],
  },
  migrationId: "migration_abc123",
});
```

### Step Configuration

```tsx
const migrationSteps = [
  {
    label: "Contacts",
    desc: "Migrating contacts and profiles",
    isFree: false,
    actions: [
      {
        function: "mailchimp_to_klaviyo_contacts",
        parameters: {
          arguments: {
            // Will be populated from stepMappings
          },
        },
        mappedAttributesStoreVar: "contactMapping",
      },
    ],
    attributeToMapWith: "contact_fields",
    mapOnError: true,
    mappedAttributesStoreVar: "contactMapping",
  },
  {
    label: "Email Templates",
    desc: "Migrating email templates",
    isFree: false,
    actions: [
      {
        function: "mailchimp_to_klaviyo_templates",
        parameters: {
          arguments: {
            selectedTemplates: [], // From selectedItems
          },
        },
        mappedAttributesStoreVar: "templateMapping",
      },
    ],
    attributeToMapWith: "",
    mapOnError: false,
    mappedAttributesStoreVar: "templateMapping",
  },
  {
    label: "Automations",
    desc: "Migrating automation workflows",
    isFree: false,
    freeLimits: {
      maxAutomations: 2,
    },
    actions: [
      {
        function: "mailchimp_to_klaviyo_automations",
        parameters: {
          arguments: {
            selectedAutomations: [], // From selectedItems
          },
        },
        mappedAttributesStoreVar: "automationMapping",
      },
    ],
    attributeToMapWith: "",
    mapOnError: false,
    mappedAttributesStoreVar: "automationMapping",
  },
];
```

### Hook Functionality

**1. Job Submission**

```tsx
const runAllChecks = () => {
  setVerifying(true);
  setStatuses(steps.map((s) => ({ status: "pending", result: null })));
  setCurrentStepIndex(0);
  // Triggers first step via useEffect
};
```

**2. Job Polling**

```tsx
const pollJobStatus = (job_id: string, idx: number) => {
  const interval = setInterval(async () => {
    const data = await checkAutomationStatus({ job_id });

    if (data.progress_details) {
      setProgressDetails(data.progress_details);
    }

    if (data.status === "success") {
      clearInterval(interval);
      setStatuses((prev) => {
        const newArr = [...prev];
        newArr[idx] = { status: "completed", result: data };
        return newArr;
      });

      // Trigger next step or complete
      const nextStepIndex = statuses.findIndex(
        (status, nextIdx) =>
          nextIdx > idx &&
          (status.status === "pending" || status.status === "error"),
      );

      if (nextStepIndex !== -1) {
        setCurrentStepIndex(nextStepIndex);
      } else {
        setIsCompleted(true);
      }
    } else if (data.status === "failed") {
      clearInterval(interval);
      setStatuses((prev) => {
        const newArr = [...prev];
        newArr[idx] = { status: "error", result: data };
        return newArr;
      });
      notification.error({
        message: "Migration Error",
        description: data.error,
      });
    }
  }, pollInterval);
};
```

**3. Progress Details**

```tsx
// Progress structure from backend
interface ProgressDetails {
  total_items: number;
  completed_items: number;
  current_item: string;
  percentage: number;
}

// Display progress
{
  progressDetails && (
    <MigrationProgressBar
      completed={progressDetails.completed_items}
      total={progressDetails.total_items}
      currentItem={progressDetails.current_item}
      percentage={progressDetails.percentage}
    />
  );
}
```

## Configure Step (StepMigration)

### Item Selection Pattern

```tsx
const StepMigration: React.FC<Props> = ({
  source,
  destination,
  baseWorkflowId,
  stepData,
  setCurrent,
  stepMappings,
  setStepMappings,
}) => {
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [workflowData, setWorkflowData] = useState<any>(null);

  // Fetch available workflows/items to migrate
  const { data } = useQuery({
    queryKey: ["baseWorkflow", baseWorkflowId],
    queryFn: () => getOrCreateBaseWorkflow(baseWorkflowId),
  });

  // Transform backend workflow structure to flat list
  const transformedWorkflows = useMemo(() => {
    if (!data?.data?.workflows) return [];
    return transformWorkflowsToFlat(data.data.workflows);
  }, [data]);

  // Group by category
  const groupedByCategory = useMemo(() => {
    const grouped: Record<string, TransformedWorkflow[]> = {};
    transformedWorkflows.forEach((workflow) => {
      const category = workflow.category || "Other";
      if (!grouped[category]) grouped[category] = [];
      grouped[category].push(workflow);
    });
    return grouped;
  }, [transformedWorkflows]);

  // Handle item selection
  const handleCheckboxChange = (key: string, checked: boolean) => {
    setSelectedKeys((prev) =>
      checked ? [...prev, key] : prev.filter((k) => k !== key),
    );
  };

  // Start migration
  const handleStartMigration = () => {
    const selectedWorkflows = transformedWorkflows.filter((w) =>
      selectedKeys.includes(w.key),
    );

    const migrationSteps = selectedWorkflows.map(createMigrationStep);

    // Store selected items in step mappings
    setStepMappings((prev) => ({
      ...prev,
      selectedItems: {
        automations: selectedWorkflows
          .filter((w) => w.category === "Automations")
          .map((w) => w.id),
        templates: selectedWorkflows
          .filter((w) => w.category === "Email Templates")
          .map((w) => w.id),
        campaigns: selectedWorkflows
          .filter((w) => w.category === "Campaigns")
          .map((w) => w.id),
      },
    }));

    // Initialize automation hook with selected steps
    runAllChecks();
  };

  return (
    <div>
      {Object.entries(groupedByCategory).map(([category, workflows]) => (
        <div key={category}>
          <h3>{category}</h3>
          {workflows.map((workflow) => (
            <Checkbox
              key={workflow.key}
              checked={selectedKeys.includes(workflow.key)}
              onChange={(e) =>
                handleCheckboxChange(workflow.key, e.target.checked)
              }
            >
              {workflow.label} - {workflow.desc}
            </Checkbox>
          ))}
        </div>
      ))}

      <Button type="primary" onClick={handleStartMigration}>
        Start Migration
      </Button>
    </div>
  );
};
```

### Key Patterns

**1. Workflow Transformation**

```tsx
// Backend structure (hierarchical)
{
  workflows: [
    {
      label: "Contacts",
      children: [
        { label: "Import Contacts", key: "import_contacts" },
        { label: "Export Tags", key: "export_tags" },
      ],
    },
  ];
}

// Frontend structure (flat)
[
  { key: "contacts", label: "Contacts", category: "Data", isFree: false },
  {
    key: "import_contacts",
    label: "Import Contacts",
    category: "Data",
    isFree: false,
    parentKey: "contacts",
  },
  {
    key: "export_tags",
    label: "Export Tags",
    category: "Data",
    isFree: false,
    parentKey: "contacts",
  },
];
```

**2. Free vs Paid Items**

```tsx
const PRICING_CONFIG: Record<
  string,
  { model: "unit" | "flat"; price: number }
> = {
  automation: { model: "unit", price: 10 },
  template: { model: "unit", price: 10 },
  campaign: { model: "unit", price: 10 },
  tags: { model: "flat", price: 50 },
  segments: { model: "flat", price: 30 },
};

// Calculate total price
const calculatePrice = (selectedItems: SelectedItems) => {
  let total = 0;

  selectedItems.automations.forEach(() => {
    total += PRICING_CONFIG.automation.price;
  });

  // Flat fee items charged once
  if (selectedItems.tags.length > 0) {
    total += PRICING_CONFIG.tags.price;
  }

  return total;
};
```

**3. Payment Integration**

```tsx
const handlePayment = async () => {
  // Create payment intent
  const response = await createPaymentIntent({
    selectedItems,
    migrationId,
    source,
    destination,
  });

  // Open payment modal
  setPaymentModalVisible(true);
  setClientSecret(response.data.clientSecret);
};

// Payment modal
<PaymentModal
  visible={paymentModalVisible}
  clientSecret={clientSecret}
  amount={totalAmount}
  onSuccess={() => {
    setPaymentModalVisible(false);
    handleStartMigration();
  }}
  onCancel={() => setPaymentModalVisible(false)}
/>;
```

## Progress Sidebar

### Real-time Progress Display

```tsx
const StepMigrationSidebar: React.FC<{
  migrationResults: any[];
  progressDetails: ProgressDetails | null;
}> = ({ migrationResults, progressDetails }) => {
  return (
    <div>
      <h3>Migration Progress</h3>

      {/* Overall progress */}
      {progressDetails && (
        <div>
          <Progress
            percent={progressDetails.percentage}
            status="active"
            strokeColor="#52c41a"
          />
          <p>
            {progressDetails.completed_items} / {progressDetails.total_items}{" "}
            items
          </p>
          {progressDetails.current_item && (
            <p>Current: {progressDetails.current_item}</p>
          )}
        </div>
      )}

      {/* Individual step statuses */}
      {migrationResults.map((result, index) => (
        <div key={index}>
          {getStatusIcon(result.status)}
          <span>{result.label}</span>
          <span>{getStatusLabel(result.status)}</span>
        </div>
      ))}
    </div>
  );
};
```

### Status Mapping

```tsx
const STATUS_MAP: Record<string, string> = {
  loading: "migrating",
  waiting: "migrating",
  running: "migrating",
  success: "completed",
  completed: "completed",
  error: "error",
  failed: "error",
  pending: "pending",
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case "completed":
      return <CheckCircleOutlined style={{ color: "#52c41a" }} />;
    case "migrating":
      return <LoadingOutlined style={{ color: "#1890ff" }} />;
    case "error":
      return <CloseCircleOutlined style={{ color: "#ff4d4f" }} />;
    case "pending":
      return <ClockCircleOutlined style={{ color: "#d9d9d9" }} />;
    default:
      return null;
  }
};
```

## Complete Step

### Results Display

```tsx
const StepComplete: React.FC<Props> = ({
  source,
  destination,
  stepMappings,
  selectedItems,
  progressDetails,
}) => {
  const { migrationStatuses, migrationResults } = useMigrationStep();

  const successCount = migrationResults.filter(
    (r) => r.status === "completed",
  ).length;
  const errorCount = migrationResults.filter(
    (r) => r.status === "error",
  ).length;

  return (
    <div>
      <Result
        status={errorCount === 0 ? "success" : "warning"}
        title={
          errorCount === 0
            ? "Migration Completed Successfully!"
            : "Migration Completed with Some Errors"
        }
        subTitle={`${successCount} items migrated successfully${errorCount > 0 ? `, ${errorCount} errors` : ""}`}
      />

      {/* Summary stats */}
      <div>
        <Statistic title="Total Items" value={progressDetails?.total_items} />
        <Statistic title="Completed" value={progressDetails?.completed_items} />
        <Statistic title="Success Rate" value={`${successRate}%`} />
      </div>

      {/* Individual results */}
      {migrationResults.map((result) => (
        <Card key={result.key}>
          <div>
            {getStatusIcon(result.status)}
            <span>{result.label}</span>
          </div>
          {result.status === "error" && (
            <Alert type="error" message={result.error} />
          )}
        </Card>
      ))}

      <Button type="primary" onClick={() => navigate("/migrations")}>
        View All Migrations
      </Button>
    </div>
  );
};
```

## Context Management

### MigrationStepContext

```tsx
import React, { createContext, useContext, useState } from "react";

interface MigrationStepContextType {
  currentStep: number;
  setCurrentStep: (step: number) => void;
  migrationId: string | null;
  setMigrationId: (id: string | null) => void;
  migrationStatuses: Record<string, any>;
  setMigrationStatuses: (statuses: Record<string, any>) => void;
  migrationResults: any[];
  setMigrationResults: (results: any[]) => void;
}

const MigrationStepContext = createContext<
  MigrationStepContextType | undefined
>(undefined);

export const MigrationStepProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [migrationId, setMigrationId] = useState<string | null>(null);
  const [migrationStatuses, setMigrationStatuses] = useState<
    Record<string, any>
  >({});
  const [migrationResults, setMigrationResults] = useState<any[]>([]);

  return (
    <MigrationStepContext.Provider
      value={{
        currentStep,
        setCurrentStep,
        migrationId,
        setMigrationId,
        migrationStatuses,
        setMigrationStatuses,
        migrationResults,
        setMigrationResults,
      }}
    >
      {children}
    </MigrationStepContext.Provider>
  );
};

export const useMigrationStep = () => {
  const context = useContext(MigrationStepContext);
  if (!context) {
    throw new Error(
      "useMigrationStep must be used within MigrationStepProvider",
    );
  }
  return context;
};
```

## Local Storage Pattern

### Duplicate Detection

```tsx
// Store source/destination emails for duplicate detection
useEffect(() => {
  if (sourceEmail) {
    localStorage.setItem("migration_source_email", sourceEmail);
  }
  if (destinationEmail) {
    localStorage.setItem("migration_destination_email", destinationEmail);
  }
}, [sourceEmail, destinationEmail]);

// Backend uses these to skip duplicates
const payload = {
  actions: migrationSteps.actions,
  selectedItems,
  migrationIdentifier: {
    migrationId,
    fromEmail: localStorage.getItem("migration_source_email"),
    toEmail: localStorage.getItem("migration_destination_email"),
  },
  skipDuplicates: true,
};
```

## Error Handling

### Retry Logic

```tsx
const retryFailedChecks = () => {
  // Find failed and pending steps
  const failedSteps = statuses
    .map((status, idx) => ({ idx, status: status.status }))
    .filter(({ status }) => status === "error" || status === "pending");

  if (failedSteps.length === 0) return;

  // Reset failed steps to pending
  setStatuses((prev) => {
    const newArr = [...prev];
    failedSteps.forEach(({ idx }) => {
      newArr[idx] = { status: "pending", result: null };
    });
    return newArr;
  });

  // Start with first failed step
  setCurrentStepIndex(failedSteps[0].idx);
  setVerifying(true);
};
```

### Mapper Modal for Errors

```tsx
// If migration fails due to missing mappings
if (data.status === "success" && steps[idx].mapOnError) {
  // Open modal for user to map values
  const values = data.result?.workflow_data?.[attributeToMap];
  setMapperValues(values);
  setMapperModalOpen(true);
  return; // Wait for user input
}

// Handle user mapping
const handleMapperSubmit = (mapping: Record<string, string>) => {
  // Add mapping to step parameters
  setStepMappings((prev) => ({ ...prev, [mapperAttribute]: mapping }));
  setMapperModalOpen(false);
  setVerifying(true); // Resume workflow
};
```

## Best Practices

1. **Always gate migrations with OAuth checks** before allowing users to proceed
2. **Store step data in stepMappings** for access in later steps
3. **Use React Query** for data fetching with proper cache management
4. **Poll backend for job status** instead of waiting synchronously
5. **Track analytics events** for each migration step (started, completed, error)
6. **Provide real-time progress** with percentage and current item
7. **Allow retry for failed steps** without restarting entire migration
8. **Handle payment before migration** for paid items
9. **Use context for global state** (current step, statuses, results)
10. **Store emails in localStorage** for duplicate detection across sessions

## Common Pitfalls

❌ **Not checking OAuth before migration**

```tsx
// BAD: Start migration without checking connections
handleStartMigration();
```

✅ **Check OAuth status first**

```tsx
// GOOD: Verify connections before proceeding
const isConnected = await checkOAuthStatus();
if (!isConnected) {
  navigate("/integrations");
  return;
}
```

❌ **Polling without cleanup**

```tsx
// BAD: Memory leak if component unmounts
setInterval(() => pollStatus(), 5000);
```

✅ **Clean up intervals**

```tsx
// GOOD: Clear interval on unmount
useEffect(() => {
  const interval = setInterval(() => pollStatus(), 5000);
  return () => clearInterval(interval);
}, []);
```

❌ **Not handling partial failures**

```tsx
// BAD: Treat any error as complete failure
if (errors.length > 0) {
  showError("Migration failed");
}
```

✅ **Allow partial success**

```tsx
// GOOD: Show results with both successes and errors
const successCount = results.filter((r) => r.status === "completed").length;
const errorCount = results.filter((r) => r.status === "error").length;
showResults({ successCount, errorCount });
```

## Integration Example

Complete migration workflow:

1. **User visits `/migrations/run/{id}`**
2. **System fetches migration config** (source, destination, available items)
3. **Check OAuth connections** for both platforms
4. **Step 1: Install** - Verify native app installed
5. **Step 2: Verify** - Run verification jobs, store emails
6. **Step 3: Configure** - User selects items, initiates payment if needed
7. **System starts migration** - Submit jobs to backend
8. **Poll for progress** - Update UI every 5 seconds
9. **Step 4: Complete** - Show results, allow retry for failures
10. **Track analytics** - Send completion events

## Next Steps

- See `reference/job-polling-patterns.md` for advanced polling strategies
- Check backend custom functions for migration function signatures
- Review `reference/payment-integration.md` for Stripe integration details
- See `building-playwright-migrations` skill for creating migration functions
