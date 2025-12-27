---
name: building-antd-forms
description: Build forms with Ant Design in the React frontend. Covers custom FormInput component, type-safe validation, dynamic form fields, file uploads, and integration with React Query for API calls. Use when creating new forms, adding validation, or handling complex form interactions.
---

# Building Ant Design Forms

Create forms using Ant Design components for the Beena automation frontend. Focuses on the project's custom patterns, type safety, and integration with the backend API.

## When to Use This Skill

- Creating new authentication, registration, or user input forms
- Adding validation rules to form fields
- Implementing file upload functionality
- Building dynamic forms based on workflow configuration
- Integrating forms with backend API using React Query
- Handling complex validation logic (dependent fields, custom validators)
- Working with form state management and programmatic control

## Core Form Pattern

### Basic Form Structure

The project uses a consistent pattern with the custom `FormInput` component:

```tsx
import { Form, Button, Row, Col } from "antd";
import FormInput from "@/components/atoms/FormInput";
import { FormValues } from "@/shared/types";

interface FormProps {
  onSubmit: (values: FormValues) => void;
  isLoading: boolean;
}

const MyForm = ({ onSubmit, isLoading }: FormProps) => {
  return (
    <Form<FormValues>
      labelCol={{ span: 8 }}
      wrapperCol={{
        xs: { offset: 0, span: 8 },
        md: { offset: 8, span: 8 },
      }}
      onFinish={onSubmit}
      disabled={isLoading}
    >
      <FormInput
        name="email"
        placeholder="Email address"
        rules={[
          { required: true, message: "Please input your email!" },
          { type: "email", message: "Please enter a valid email!" },
        ]}
      />

      <Form.Item>
        <Row justify="center">
          <Col span={24}>
            <Button
              type="primary"
              htmlType="submit"
              loading={isLoading}
              block
              style={{ backgroundColor: "#369EFF", height: "40px" }}
            >
              Submit
            </Button>
          </Col>
        </Row>
      </Form.Item>
    </Form>
  );
};

export default MyForm;
```

**Key features:**

- Type-safe with `Form<FormValues>` generic
- Responsive layout with `labelCol` and `wrapperCol`
- Custom FormInput component for consistency
- Disabled state during submission
- Primary button styling: `#369EFF` background, 40px height

## Custom FormInput Component

Located at `src/components/atoms/FormInput/index.tsx`:

```tsx
import { Input, Form } from "antd";
import { EyeOutlined, EyeInvisibleOutlined } from "@ant-design/icons";
import { useState } from "react";

interface FormInputProps {
  name: string;
  placeholder: string;
  type?: "text" | "password";
  rules?: any[];
  label?: string;
  initialValue?: string;
  disabled?: boolean;
}

const FormInput = ({
  name,
  placeholder,
  initialValue,
  type = "text",
  rules = [],
  label,
  disabled,
}: FormInputProps) => {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <Form.Item
      initialValue={initialValue}
      name={name}
      rules={rules}
      label={label}
    >
      {type === "password" ? (
        <Input.Password
          disabled={disabled}
          placeholder={placeholder}
          iconRender={(visible) =>
            visible ? (
              <EyeOutlined onClick={() => setShowPassword(false)} />
            ) : (
              <EyeInvisibleOutlined onClick={() => setShowPassword(true)} />
            )
          }
          visibilityToggle={{
            visible: showPassword,
            onVisibleChange: setShowPassword,
          }}
        />
      ) : (
        <Input disabled={disabled} placeholder={placeholder} />
      )}
    </Form.Item>
  );
};

export default FormInput;
```

**Usage:**

```tsx
<FormInput
  name="password"
  placeholder="Create Password"
  type="password"
  rules={[
    { required: true, message: "Please input your password!" },
    { min: 6, message: "Password must be at least 6 characters!" },
  ]}
/>
```

## Common Validation Patterns

### Required Field

```tsx
<FormInput
  name="fullName"
  placeholder="Full Name"
  rules={[{ required: true, message: "Please input your full name!" }]}
/>
```

### Email Validation

```tsx
<FormInput
  name="email"
  placeholder="Email address"
  rules={[
    { required: true, message: "Please input your email!" },
    { type: "email", message: "Please enter a valid email!" },
  ]}
/>
```

### Password with Minimum Length

```tsx
<FormInput
  name="password"
  placeholder="Password"
  type="password"
  rules={[
    { required: true, message: "Please input your password!" },
    { min: 6, message: "Password must be at least 6 characters!" },
  ]}
/>
```

### Password Confirmation (Dependent Field)

```tsx
<FormInput
  name="confirmPassword"
  placeholder="Confirm Password"
  type="password"
  rules={[
    { required: true, message: "Please confirm your password!" },
    ({ getFieldValue }: { getFieldValue: (field: string) => string }) => ({
      validator(_: unknown, value: string) {
        if (!value || getFieldValue("password") === value) {
          return Promise.resolve();
        }
        return Promise.reject(new Error("Passwords do not match!"));
      },
    }),
  ]}
/>
```

**Pattern explanation:**

- Custom validator receives form instance with `getFieldValue`
- Compares current field value with dependent field
- Returns Promise.resolve() on success, Promise.reject() with error message on failure

### Conditional Fields

```tsx
<FormInput
  name="migrateFrom"
  placeholder="Migrate from website url"
  initialValue={initialValues?.migrateFrom}
  rules={[]}
  disabled={!!initialValues?.migrateFrom} // Disable if pre-populated
/>
```

## Form Hooks and Programmatic Control

### Using Form.useForm()

For programmatic form control:

```tsx
import { Form } from "antd";
import { useEffect } from "react";

export const useFormManager = (currentTask: TaskData | null) => {
  const [form] = Form.useForm();

  // Initialize form with data
  useEffect(() => {
    if (currentTask) {
      form.resetFields();
      form.setFieldsValue({
        ...currentTask,
        // Additional transformations
      });
    }
  }, [currentTask, form]);

  return { form };
};
```

**Common methods:**

- `form.resetFields()` - Clear all fields
- `form.setFieldsValue(values)` - Set field values programmatically
- `form.getFieldValue(name)` - Get single field value
- `form.getFieldsValue()` - Get all field values
- `form.validateFields()` - Trigger validation manually

**Usage in component:**

```tsx
const MyForm = () => {
  const { form } = useFormManager(taskData);

  return <Form form={form}>{/* form fields */}</Form>;
};
```

## File Upload Forms

### Upload Configuration

```tsx
import { Upload, Button, UploadProps } from "antd";
import { UploadOutlined } from "@ant-design/icons";

const props: UploadProps = {
  beforeUpload: (_file) => {
    return false; // Prevent auto-upload, handle manually
  },
};

<Form.Item
  name="csvFile"
  valuePropName="fileList" // Important: use fileList for file data
  getValueFromEvent={(e) => {
    if (Array.isArray(e)) {
      return e;
    }
    return e && e.fileList;
  }}
>
  <Upload {...props} maxCount={1}>
    <Button icon={<UploadOutlined />}>Upload Excel(.xlsx, csv)</Button>
  </Upload>
</Form.Item>;
```

**Key points:**

- `valuePropName="fileList"` instead of default "value"
- `getValueFromEvent` extracts fileList from upload event
- `beforeUpload: () => false` prevents automatic upload
- `maxCount={1}` limits to single file

### Multi-File Upload

```tsx
<Upload {...props} name="documents" maxCount={5} multiple>
  <Button icon={<UploadOutlined />}>Upload Documents (Max 5)</Button>
</Upload>
```

### Dynamic Upload Inputs

Based on workflow configuration:

```tsx
{
  Array.from({ length: numberOfUploads }).map((_, i) => (
    <Form.Item
      key={`upload-${i}`}
      name={[`input_${actionName}_${i}`]}
      valuePropName="fileList"
      getValueFromEvent={(e) => {
        if (Array.isArray(e)) {
          return e;
        }
        return e && e.fileList;
      }}
    >
      <Upload {...props} maxCount={1}>
        <Button icon={<UploadOutlined />}>Upload CSV Instance {i + 1}</Button>
      </Upload>
    </Form.Item>
  ));
}
```

## API Integration with React Query

### Form Submission with useMutation

```tsx
import { useMutation } from "@tanstack/react-query";
import { message } from "antd";
import { loginUser } from "@/shared/services/auth";

const LoginPage = () => {
  const { mutate: login, isLoading } = useMutation({
    mutationFn: (data: LoginRequest) => loginUser(data),
    onSuccess: (response) => {
      message.success("Login successful");
      // Navigate or update state
    },
    onError: (error: any) => {
      message.error(error?.response?.data?.message || "Login failed");
    },
  });

  const handleSubmit = (values: LoginRequest) => {
    login(values);
  };

  return <LoginForm onSubmit={handleSubmit} isLoading={isLoading} />;
};
```

**Pattern:**

1. Define mutation with `useMutation`
2. Extract `mutate` function and `isLoading` state
3. Pass `isLoading` to form to disable during submission
4. Call `mutate(values)` in form's `onFinish` handler
5. Show success/error messages using `message` from antd

### FormData Submission (File Uploads)

```tsx
import { updateMultiPartUserWorkflow } from "@/shared/services/admins/dashboard";

const handleSubmit = async (values: any) => {
  const formData = new FormData();

  // Add text fields
  formData.append("name", values.name);
  formData.append("description", values.description);

  // Add file uploads
  if (values.csvFile && values.csvFile[0]) {
    formData.append("file", values.csvFile[0].originFileObj);
  }

  // Send to API
  const { mutate: updateWorkflow } = useMutation({
    mutationFn: (id: string) => updateMultiPartUserWorkflow(id, formData),
    onSuccess: () => {
      message.success("Workflow updated successfully");
    },
  });

  updateWorkflow(workflowId);
};
```

**Important:**

- Use `FormData` for multipart/form-data requests
- Access file via `fileList[0].originFileObj`
- API service should accept `FormData` type
- Content-Type header automatically set by axios

## Dynamic Forms Based on Configuration

### Rendering Different Input Types

```tsx
const renderActionSpecificUI = (input: any, index: number, type: string) => {
  const totalInputs = input.numberOfInputs;
  const actionName = input.actionName;

  switch (input.type) {
    case "upload_csv":
      return (
        <div key={index}>
          <h4>{actionName}</h4>
          {Array.from({ length: totalInputs }).map((_, i) => (
            <Form.Item
              key={`action-${index}-upload-${i}`}
              name={[`${type}_${actionName}_${i}`]}
              valuePropName="fileList"
              getValueFromEvent={(e) => {
                if (Array.isArray(e)) return e;
                return e && e.fileList;
              }}
            >
              <Upload {...uploadProps} maxCount={1}>
                <Button icon={<UploadOutlined />}>
                  Upload Excel(.xlsx, csv)
                </Button>
              </Upload>
            </Form.Item>
          ))}
        </div>
      );

    case "input_field":
      return (
        <div key={index}>
          <h4>{actionName || `${type} Field ${index + 1}`}</h4>
          {Array.from({ length: totalInputs }).map((_, i) => (
            <Form.Item
              key={`action-${index}-input-${i}`}
              name={[`${type}_${actionName}_${i}`]}
            >
              <Input placeholder="Enter value" style={{ width: "40%" }} />
            </Form.Item>
          ))}
        </div>
      );

    default:
      return null;
  }
};

// Usage in form
{
  requiredFiles?.input?.map((input: any, index: number) =>
    renderActionSpecificUI(input, index, "input"),
  );
}
```

**Pattern explanation:**

- Switch on input.type to render appropriate component
- Generate multiple inputs based on numberOfInputs
- Use array notation for form names: `[type_name_index]`
- Return null for unknown types (graceful degradation)

## Form Layout Patterns

### Responsive Layout (Project Standard)

```tsx
<Form
  labelCol={{ span: 8 }}
  wrapperCol={{
    xs: { offset: 0, span: 8 }, // Mobile: full width
    md: { offset: 8, span: 8 }, // Desktop: centered
  }}
>
  {/* form fields */}
</Form>
```

### Centered Submit Button

```tsx
<Form.Item>
  <Row justify="center">
    <Col span={24}>
      <Button
        type="primary"
        htmlType="submit"
        loading={isLoading}
        block
        style={{ backgroundColor: "#369EFF", height: "40px" }}
      >
        Submit
      </Button>
    </Col>
  </Row>
</Form.Item>
```

### Inline Form

```tsx
<Form layout="inline">
  <Form.Item name="search">
    <Input placeholder="Search..." />
  </Form.Item>
  <Form.Item>
    <Button type="primary" htmlType="submit">
      Search
    </Button>
  </Form.Item>
</Form>
```

## TypeScript Integration

### Form Values Type

Define types for form data:

```tsx
// src/shared/types/auth.ts
export interface RegisterFormValues {
  registerName: string;
  registerEmail: string;
  registerMigrateFrom?: string;
  registerMigrateTo?: string;
  registerPassword: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}
```

### Type-Safe Form Component

```tsx
import { Form } from "antd";
import { RegisterFormValues } from "@/shared/types/auth";

const RegisterForm = ({ onSubmit }: RegisterFormProps) => {
  return (
    <Form<RegisterFormValues> // Generic type parameter
      onFinish={onSubmit} // onSubmit receives RegisterFormValues
    >
      {/* fields */}
    </Form>
  );
};
```

### Type-Safe Props

```tsx
interface FormProps {
  onSubmit: (values: RegisterFormValues) => void;
  isLoading: boolean;
  initialValues?: Partial<RegisterFormValues>;
}
```

## Error Handling

### Display API Errors

```tsx
import { message } from "antd";

const { mutate: submitForm, isLoading } = useMutation({
  mutationFn: (data: FormValues) => apiCall(data),
  onSuccess: () => {
    message.success("Form submitted successfully");
  },
  onError: (error: any) => {
    const errorMessage =
      error?.response?.data?.message || "An error occurred. Please try again.";
    message.error(errorMessage);
  },
});
```

### Field-Level Errors

```tsx
const [form] = Form.useForm();

// Set error on specific field
form.setFields([
  {
    name: "email",
    errors: ["This email is already registered"],
  },
]);
```

### Show Warning Messages

```tsx
import { ExclamationCircleFilled } from "@ant-design/icons";
import { Card } from "antd";

<Card>
  <div style={{ marginBottom: 10, display: "flex", alignItems: "center" }}>
    <ExclamationCircleFilled style={{ marginRight: 4, color: "orange" }} />
    <h4>Actions Required</h4>
  </div>
  {/* form content */}
</Card>;
```

## Best Practices

1. **Always use FormInput component** for text/password inputs (project standard)
2. **Type-safe forms** with `Form<T>` generic and TypeScript interfaces
3. **Consistent layout** with labelCol/wrapperCol pattern (xs mobile, md desktop)
4. **Disable during submission** using `disabled={isLoading}` on Form
5. **Loading states** on submit button with `loading={isLoading}`
6. **Project button styling** - #369EFF background, 40px height, block layout
7. **File uploads** - Always use `valuePropName="fileList"` and `getValueFromEvent`
8. **Custom validators** - Return Promise.resolve/reject for async validation
9. **Error messages** - Use Ant Design's `message` component for user feedback
10. **Form hooks** - Use `Form.useForm()` for programmatic control

## Common Pitfalls

❌ **Using Input directly without FormInput**

```tsx
// BAD: Inconsistent with project pattern
<Form.Item name="email">
  <Input placeholder="Email" />
</Form.Item>
```

✅ **Use FormInput component**

```tsx
// GOOD: Project standard
<FormInput name="email" placeholder="Email" rules={[...]} />
```

❌ **Missing type parameter on Form**

```tsx
// BAD: No type safety
<Form onFinish={onSubmit}>
```

✅ **Type-safe form**

```tsx
// GOOD: Type-checked
<Form<LoginRequest> onFinish={onSubmit}>
```

❌ **Wrong file upload configuration**

```tsx
// BAD: Missing required props
<Form.Item name="file">
  <Upload>
    <Button>Upload</Button>
  </Upload>
</Form.Item>
```

✅ **Correct file upload**

```tsx
// GOOD: All required props
<Form.Item
  name="file"
  valuePropName="fileList"
  getValueFromEvent={(e) => (Array.isArray(e) ? e : e && e.fileList)}
>
  <Upload beforeUpload={() => false} maxCount={1}>
    <Button>Upload</Button>
  </Upload>
</Form.Item>
```

## Integration Example

Complete example integrating form, validation, and API:

```tsx
import { Form, Button, Row, Col, message } from "antd";
import { useMutation } from "@tanstack/react-query";
import FormInput from "@/components/atoms/FormInput";
import { registerUser } from "@/shared/services/auth";
import { RegisterFormValues } from "@/shared/types/auth";

interface RegisterFormProps {
  onSuccess: () => void;
}

const RegisterForm = ({ onSuccess }: RegisterFormProps) => {
  const { mutate: register, isLoading } = useMutation({
    mutationFn: (data: RegisterFormValues) => registerUser(data),
    onSuccess: () => {
      message.success("Registration successful!");
      onSuccess();
    },
    onError: (error: any) => {
      message.error(
        error?.response?.data?.message ||
          "Registration failed. Please try again.",
      );
    },
  });

  const handleSubmit = (values: RegisterFormValues) => {
    register(values);
  };

  return (
    <Form<RegisterFormValues>
      labelCol={{ span: 8 }}
      wrapperCol={{
        xs: { offset: 0, span: 8 },
        md: { offset: 8, span: 8 },
      }}
      onFinish={handleSubmit}
      disabled={isLoading}
    >
      <FormInput
        name="registerName"
        placeholder="Full Name"
        rules={[{ required: true, message: "Please input your full name!" }]}
      />

      <FormInput
        name="registerEmail"
        placeholder="Email address"
        rules={[
          { required: true, message: "Please input your email!" },
          { type: "email", message: "Please enter a valid email!" },
        ]}
      />

      <FormInput
        name="registerPassword"
        placeholder="Create Password"
        type="password"
        rules={[
          { required: true, message: "Please input your password!" },
          { min: 6, message: "Password must be at least 6 characters!" },
        ]}
      />

      <Form.Item>
        <Row justify="center">
          <Col span={24}>
            <Button
              type="primary"
              htmlType="submit"
              loading={isLoading}
              block
              style={{ backgroundColor: "#369EFF", height: "40px" }}
            >
              Create an account
            </Button>
          </Col>
        </Row>
      </Form.Item>
    </Form>
  );
};

export default RegisterForm;
```

## Next Steps

- See `reference/advanced-patterns.md` for complex form scenarios
- Check `reference/validation-cookbook.md` for more validation examples
- Review existing forms in `src/components/organisms/` for real implementations
