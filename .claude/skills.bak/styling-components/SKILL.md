# styling-components

## Description

Style React components using styled-components in the Beena frontend application. Covers wrapping Ant Design components, creating custom styled components, conditional styling with props, global styles, theme integration, and co-locating styles with components.

## When to Use

- Creating new UI components that need custom styling
- Overriding Ant Design component styles
- Implementing responsive design with media queries
- Adding conditional styling based on props or state
- Setting up global styles or theme variables
- Organizing component-specific styles in separate files
- Creating reusable styled components across the application

## Prerequisites

- Understanding of CSS-in-JS concepts
- Familiarity with React and TypeScript
- Knowledge of Ant Design component library
- Basic understanding of CSS selectors and properties

## Key Concepts

### Styled-Components Basics

Styled-components is a CSS-in-JS library that allows you to write CSS directly in TypeScript/JavaScript files:

```typescript
import styled from "styled-components";

// Basic styled component
const Button = styled.button`
  background-color: #1890ff;
  color: white;
  padding: 8px 16px;
  border-radius: 4px;
  border: none;
  cursor: pointer;

  &:hover {
    background-color: #40a9ff;
  }
`;
```

### Project File Organization

Styles are organized in two ways:

1. **Co-located styles** - `styles.ts` or `styles.tsx` next to component

   ```
   components/
   ├── MigrationProgressBar/
   │   ├── index.tsx
   │   └── styles.ts
   ```

2. **Shared styles** - Common styles in `src/shared/styles/`
   ```
   shared/styles/
   ├── globalStyles.ts      # App-wide CSS reset and defaults
   ├── components.ts        # Reusable styled components
   ├── authStyles.ts        # Auth page specific styles
   └── styled.d.ts          # TypeScript definitions
   ```

## Implementation Patterns

### 1. Creating Custom Styled Components

Define styled components for basic HTML elements:

```typescript
// components/molecules/MigrationProgressBar/styles.ts
import styled from "styled-components";

export const ProgressContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-self: stretch;
  gap: 8px;
  margin-bottom: 16px;
`;

export const ProgressHeader = styled.div`
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  align-self: stretch;
  gap: 97px;
`;

export const ProgressTitle = styled.span`
  font-family: "DM Sans", sans-serif;
  font-weight: 700;
  font-size: 12px;
  line-height: 1.3333333333333333em;
  color: #333333;
`;

export const ProgressCount = styled.span`
  font-family: "DM Sans", sans-serif;
  font-weight: 400;
  font-size: 12px;
  line-height: 1.3333333333333333em;
  color: #333333;
`;
```

**Usage**:

```typescript
import { ProgressContainer, ProgressHeader, ProgressTitle, ProgressCount } from './styles';

const MigrationProgressBar: React.FC<Props> = ({ title, current, total }) => {
  return (
    <ProgressContainer>
      <ProgressHeader>
        <ProgressTitle>{title}</ProgressTitle>
        <ProgressCount>{current}/{total}</ProgressCount>
      </ProgressHeader>
      {/* Progress bar */}
    </ProgressContainer>
  );
};
```

### 2. Styling Ant Design Components

Wrap Ant Design components to customize their appearance:

```typescript
// shared/styles/components.ts
import { Card, Tag } from "antd";
import { styled } from "styled-components";

export const StyledTag = styled(Tag)`
  font-size: 12px;
  border-radius: 10px;
  border: none;
  padding: 4px 8px;
  text-align: center;
  min-width: 88px;
`;

export const StyledPill = styled(Tag)`
  font-size: 12px;
  font-weight: bold;
  padding: 5px 10px;
  border-radius: 5px;
  min-width: 130px;
  text-align: center;
`;

export const WorkerReviewVerticalCard = styled(Card)`
  border: 1px solid #f0f0f0;
  margin: 24px 0;

  .ant-card-body {
    padding: 0 !important;
  }

  .comparable-item-row {
    background-color: #fbe9eb;
  }

  .worker-review-input {
    margin-top: 25px;
    margin-right: 10px;
    min-width: 250px;
    margin-left: auto;
  }
`;
```

**Overriding Ant Design Component Styles**:

```typescript
import { Progress } from "antd";
import styled from "styled-components";

export const StyledProgress = styled(Progress)`
  .ant-progress-bg {
    background-color: #369eff !important;
  }

  .ant-progress-outer {
    padding-right: 0 !important;
  }

  .ant-progress-inner {
    background-color: #f0f0f0 !important;
    border-radius: 100px !important;
    height: 8px !important;
  }

  .ant-progress-bg {
    border-radius: 100px !important;
    height: 8px !important;
  }
`;
```

**Note**: Use `!important` sparingly, only when Ant Design's inline styles need overriding.

### 3. Conditional Styling with Props

Use props to apply conditional styles:

```typescript
// Using transient props (prefixed with $) to avoid passing to DOM
export const DiffText = styled.div<{ $type: 'added' | 'removed' | 'normal' }>`
  background-color: ${(props) =>
    props.$type === 'added'
      ? '#e6ffe6'
      : props.$type === 'removed'
      ? 'red'
      : 'transparent'};
  color: ${(props) =>
    props.$type === 'added'
      ? '#006100'
      : props.$type === 'removed'
      ? 'white'
      : 'inherit'};
`;

// Usage
<DiffText $type="added">This text was added</DiffText>
<DiffText $type="removed">This text was removed</DiffText>
<DiffText $type="normal">This text is unchanged</DiffText>
```

**Why transient props ($type)?**

- Props prefixed with `$` are NOT passed to the underlying DOM element
- Prevents React warnings about unknown props on DOM elements
- Best practice in styled-components v5.1+

### 4. Global Styles

Define app-wide styles using `createGlobalStyle`:

```typescript
// shared/styles/globalStyles.ts
import { createGlobalStyle } from "styled-components";

export const GlobalStyle = createGlobalStyle`
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    font-family: 'DM Sans', sans-serif;
  }

  :root {
    color-scheme: light dark;
    font-synthesis: none;
    text-rendering: optimizeLegibility;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  body {
    margin: 0;
    min-width: 320px;
    min-height: 100vh;
    color: rgba(255, 255, 255, 0.87);
    background-color: #242424;
  }

  h1, h2, h3, h4, h5, h6 {
    font-weight: 500;
  }

  input::placeholder {
    font-size: 14px !important;
    color: #C2C2C2 !important;
  }

  a {
    font-weight: 500;
    color: #646cff;
    text-decoration: inherit;
    &:hover {
      color: #535bf2;
    }
  }

  // Override Ant Design defaults
  .ant-layout {
    background-color: white !important;
  }

  .ant-layout-content > div {
    background-color: white !important;
  }

  @media (prefers-color-scheme: light) {
    :root {
      color: #213547;
      background-color: #ffffff;
    }
    body {
      color: #213547;
      background-color: #ffffff;
    }
  }
`;
```

**Apply global styles in main.tsx**:

```typescript
// src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { GlobalStyle } from './shared/styles/globalStyles';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <GlobalStyle />
    <App />
  </React.StrictMode>
);
```

### 5. Responsive Design with Media Queries

Add responsive behavior using CSS media queries:

```typescript
export const PageContainer = styled.div`
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;

  @media (max-width: 768px) {
    padding: 16px;
  }
`;

// Global media queries in createGlobalStyle
export const GlobalStyle = createGlobalStyle`
  @media (min-width: 1024px) {
    .view-only-config-json-editor {
      max-width: 800px !important;
      margin: 0 auto;
      overflow: auto;
    }

    .editable-config-json-editor {
      min-width: 400px !important;
      overflow: auto;
    }
  }

  @media (min-width: 1600px) {
    .view-only-config-json-editor {
      max-width: 1200px;
      margin: 0 auto;
      overflow: auto;
    }

    .editable-config-json-editor {
      min-width: 700px !important;
      overflow: auto;
    }
  }
`;
```

### 6. Nested Selectors

Target child elements using nested selectors:

```typescript
export const WorkflowActionsCard = styled(Card)`
  min-height: 79vh;
  max-height: 79vh;
  overflow-y: auto;
  border: none;

  .ant-card-head {
    position: sticky;
    top: 0;
    z-index: 10;
    background-color: #fff;
    border-bottom: none;
    margin-bottom: 14px;
  }

  h2 {
    font-weight: 500;
    font-size: 24px;
    line-height: 36px;
    letter-spacing: 0px;
  }

  .workflow-description {
    font-weight: 400;
    font-size: 14px;
    line-height: 20px;
    letter-spacing: 0px;
  }
`;

export const ActionsRequiredCard = styled(Card)`
  margin-bottom: 20px;
  background-color: #f5f5f5;

  .upload-csv-instance {
    margin: 5px 0;
  }
`;
```

### 7. Inline Style Objects (Alternative)

For simpler cases or when sharing styles across components:

```typescript
// shared/styles/components.ts
export const tableCellStyles = {
  diffText: {
    whiteSpace: "pre-wrap" as const,
    wordWrap: "break-word" as const,
    maxWidth: "fit-content",
    height: "100%",
    alignItems: "center",
    display: "flex",
    justifyContent: "center",
    padding: "0 10px",
    width: "350px",
  },
  text: {
    whiteSpace: "pre-wrap" as const,
    wordWrap: "break-word" as const,
    maxWidth: "fit-content",
    borderLeft: "3px solid white",
    height: "100%",
    alignItems: "center",
    display: "flex",
    justifyContent: "center",
    padding: "0 10px",
    width: "400px",
  },
  image: {
    width: "100px",
    height: "90%",
    padding: "0 10px",
    objectFit: "contain" as const,
  },
};

export const cardTextStyles = {
  fontSize: "14px",
  fontWeight: "600",
  color: "#000",
};

export const noTasksAvailableStyles = {
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  height: "60vh",
  fontSize: "16px",
  fontWeight: "500",
  color: "#000",
};
```

**Usage**:

```typescript
import { tableCellStyles, cardTextStyles } from '@/shared/styles/components';

<div style={tableCellStyles.text}>Cell content</div>
<span style={cardTextStyles}>Card title</span>
```

**Note**: Use `as const` for TypeScript to infer literal types instead of widening to `string`.

### 8. Complete Component Example

Putting it all together:

```typescript
// components/integrations/KlaviyoConnect/ConnectionStatus.tsx
import React from 'react';
import styled from 'styled-components';
import { Card, Button, Tag } from 'antd';

const StatusHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
`;

const StatusDetails = styled.div`
  padding: 16px;
  background: #f5f5f5;
  border-radius: 8px;
  margin-top: 16px;
`;

const AccountInfo = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
`;

const InfoLabel = styled.span`
  font-weight: 600;
  color: #666;
`;

const InfoValue = styled.span`
  color: #000;
`;

interface ConnectionStatusProps {
  connected: boolean;
  accountName?: string;
  accountId?: string;
  connectedAt?: string;
  onDisconnect: () => void;
}

const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  connected,
  accountName,
  accountId,
  connectedAt,
  onDisconnect
}) => {
  return (
    <Card>
      <StatusHeader>
        <Tag color={connected ? 'success' : 'default'}>
          {connected ? 'Connected' : 'Not Connected'}
        </Tag>
        {connected && (
          <Button danger onClick={onDisconnect}>
            Disconnect
          </Button>
        )}
      </StatusHeader>

      {connected && (
        <StatusDetails>
          <AccountInfo>
            <div>
              <InfoLabel>Account Name: </InfoLabel>
              <InfoValue>{accountName}</InfoValue>
            </div>
            <div>
              <InfoLabel>Account ID: </InfoLabel>
              <InfoValue>{accountId}</InfoValue>
            </div>
            <div>
              <InfoLabel>Connected At: </InfoLabel>
              <InfoValue>{new Date(connectedAt).toLocaleString()}</InfoValue>
            </div>
          </AccountInfo>
        </StatusDetails>
      )}
    </Card>
  );
};

export default ConnectionStatus;
```

## Best Practices

1. **Use Transient Props for Conditional Styling**

   ```typescript
   // Good - transient prop ($)
   const Box = styled.div<{ $active: boolean }>`
     background: ${(p) => (p.$active ? "blue" : "gray")};
   `;

   // Bad - regular prop passed to DOM
   const Box = styled.div<{ active: boolean }>`
     background: ${(p) => (p.active ? "blue" : "gray")};
   `;
   ```

2. **Co-locate Styles with Components**

   ```
   components/MyComponent/
   ├── index.tsx          # Component logic
   ├── styles.ts          # Styled components
   └── MyComponent.test.tsx
   ```

3. **Export Named Styled Components**

   ```typescript
   // Good
   export const Container = styled.div`...`;
   export const Header = styled.h1`...`;

   // Avoid default exports for styled components
   ```

4. **Use Global Styles Sparingly**
   - Only for CSS resets, font imports, and app-wide defaults
   - Component-specific styles should be co-located
   - Avoid global class names (defeats styled-components purpose)

5. **Leverage TypeScript for Props**

   ```typescript
   interface ButtonProps {
     $variant: "primary" | "secondary";
     $size: "small" | "medium" | "large";
   }

   const Button = styled.button<ButtonProps>`
     padding: ${(p) => (p.$size === "small" ? "4px 8px" : "8px 16px")};
     background: ${(p) => (p.$variant === "primary" ? "#1890ff" : "#fff")};
   `;
   ```

6. **Organize Shared Styles**
   - **globalStyles.ts** - App-wide CSS reset and defaults
   - **components.ts** - Reusable styled components (StyledTag, StyledCard)
   - **[feature]Styles.ts** - Feature-specific shared styles

7. **Override Ant Design Thoughtfully**

   ```typescript
   // Minimal overrides - extend Ant Design design language
   const StyledButton = styled(Button)`
     border-radius: 8px;
   `;

   // When needed, use !important for specificity
   const StyledTable = styled(Table)`
     .ant-table-thead > tr > th {
       background-color: #fafafa !important;
     }
   `;
   ```

8. **Avoid Inline Styles When Possible**

   ```typescript
   // Good - styled component
   const Header = styled.h1`
     font-size: 24px;
     font-weight: 600;
   `;

   // Bad - inline style (except for dynamic values)
   <h1 style={{ fontSize: '24px', fontWeight: 600 }}>Title</h1>
   ```

## Common Pitfalls

1. **Forgetting Transient Props Prefix**

   ```typescript
   // Wrong - prop passed to DOM element
   <Box active={true} />  // React warning

   // Correct - transient prop
   <Box $active={true} />  // No warning
   ```

2. **Using Regular Props with DOM Elements**

   ```typescript
   // Wrong
   const Input = styled.input<{ error: boolean }>`...`;
   <Input error={true} />  // 'error' passed to <input>

   // Correct
   const Input = styled.input<{ $error: boolean }>`...`;
   <Input $error={true} />
   ```

3. **Overusing !important**
   - Only use when overriding Ant Design inline styles
   - Prefer increasing specificity with nested selectors

4. **Not Using TypeScript Types**

   ```typescript
   // Wrong - no type safety
   const Box = styled.div`
     color: ${(p) => p.color};
   `;

   // Correct - typed props
   const Box = styled.div<{ $color: string }>`
     color: ${(p) => p.$color};
   `;
   ```

5. **Creating Styled Components Inside Render**

   ```typescript
   // Wrong - creates new component on every render
   const MyComponent = () => {
     const Box = styled.div`...`;
     return <Box />;
   };

   // Correct - define outside
   const Box = styled.div`...`;
   const MyComponent = () => <Box />;
   ```

6. **Mixing Styling Approaches**
   - Choose either styled-components OR inline styles, not both
   - Consistent approach improves maintainability

## TypeScript Integration

Define types for styled component props:

```typescript
// styled.d.ts - augment styled-components module
import "styled-components";

declare module "styled-components" {
  export interface DefaultTheme {
    colors: {
      primary: string;
      secondary: string;
      background: string;
      text: string;
    };
    spacing: {
      small: string;
      medium: string;
      large: string;
    };
  }
}
```

**Using theme in components**:

```typescript
import styled from "styled-components";

const Button = styled.button`
  background-color: ${(p) => p.theme.colors.primary};
  padding: ${(p) => p.theme.spacing.medium};
`;
```

## Performance Considerations

1. **Component Re-renders**
   - Styled components re-render only when props change
   - Use `React.memo()` if needed for expensive components

2. **CSS-in-JS Bundle Size**
   - Styled-components adds ~16KB gzipped
   - Tree-shaking removes unused styled components

3. **Server-Side Rendering (SSR)**
   - Styled-components supports SSR out of the box
   - Critical CSS is extracted automatically

## Related Files

- `src/shared/styles/globalStyles.ts` - Global CSS reset and defaults
- `src/shared/styles/components.ts` - Reusable styled components
- `src/shared/styles/styled.d.ts` - TypeScript theme definitions
- Component-specific `styles.ts` files throughout `src/components/`

## References

- [Styled-Components Documentation](https://styled-components.com/docs)
- [Styled-Components Best Practices](https://styled-components.com/docs/basics#best-practices)
- [Ant Design Customization](https://ant.design/docs/react/customize-theme)
- [Transient Props ($prop)](https://styled-components.com/docs/api#transient-props)
