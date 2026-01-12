# Beena Project Skills

Agent skills for the Beena automation platform (Native App, Backend, Frontend).

## Completed Skills (18/18) - 100% ✅

### Phase 1: Native App Skills ✅ (3/3)

1. **building-playwright-migrations**
   - Create ESP migration functions (Mailchimp→Klaviyo, Yotpo→Klaviyo)
   - Standard interface, DOM extraction, template building
   - Reference files: selector-strategies, examples, troubleshooting

2. **debugging-playwright-selectors**
   - Troubleshoot selector failures in browser automation
   - Iframe handling, dynamic content, fallback strategies
   - Reference files: selector-cookbook

3. **packaging-native-apps**
   - Build & package with Briefcase for macOS/Windows/Linux
   - Platform-specific dependencies, build automation
   - Reference files: platform-specific

### Phase 2: Backend Skills ✅ (3/3)

4. **implementing-oauth-flows**
   - OAuth 2.0 with PKCE in Node.js/Express
   - Token encryption, refresh logic, Clean Architecture
   - Complete implementation guide with code examples

5. **structuring-clean-architecture**
   - Organize Node.js/Express backend code following Clean Architecture
   - Layer separation (Application, Infrastructure, Interface)
   - Dependency inversion and SOLID principles

6. **creating-mongoose-schemas**
   - Design MongoDB schemas with Mongoose for automation backend
   - Indexing strategies, relationships, virtuals, middleware hooks
   - Project-specific schemas (User, Workflow, OAuthConnection)

### Phase 3: Frontend Skills ✅ (3/3)

7. **building-antd-forms**
   - Build forms with Ant Design components in React frontend
   - Custom FormInput component, type-safe validation
   - File uploads, dynamic forms, React Query integration

8. **implementing-oauth-callbacks**
   - Handle OAuth callback pages for ESP integrations
   - Three-page pattern (Install→Callback→Error)
   - Backend delegation, connection status checking

9. **managing-migration-workflows**
   - Manage ESP migration workflows in React frontend
   - Multi-step flows (Install→Verify→Configure→Complete)
   - Job polling, progress tracking, item selection, payment integration

### Phase 4: Cross-Platform Skills ✅ (9/9)

10. **extending-fastapi-server**
    - Extend FastAPI server in Native App
    - Service class pattern, middleware, dependency injection
    - Lifecycle management, error handling

11. **managing-jobstatus-communication**
    - Thread-safe IPC patterns for Native App
    - Job queue, status updates, shared variables
    - Graceful shutdown, cross-thread communication

12. **managing-environment-configs**
    - Configuration management across 3 tech stacks
    - Python ConfigManager, Node.js dotenv, Vite env vars
    - Validation, environment-specific settings

13. **tracing-migration-errors**
    - Debug errors across full stack (Native→Backend→Frontend)
    - Common error scenarios, structured logging
    - Network debugging, database inspection

14. **testing-express-apis**
    - Test Express.js APIs with Jest/Supertest
    - Factory pattern, mocking, integration tests
    - Coverage configuration, CI/CD integration

15. **validating-joi-schemas**
    - Implement Joi validation schemas for backend
    - Custom validators, error messages, middleware integration
    - Common validation patterns (email, password, ObjectId)

16. **protecting-routes**
    - Authentication & authorization middleware for Express.js
    - JWT verification, role-based access control (RBAC)
    - Route-level and router-level protection patterns

17. **debugging-oauth-integration**
    - Debug OAuth 2.0 flows (Klaviyo with PKCE)
    - Common errors (state validation, token refresh, encryption)
    - Testing techniques, environment configuration

18. **styling-components**
    - Style React components using styled-components
    - Wrap Ant Design components, conditional styling with props
    - Global styles, responsive design, TypeScript integration

## Skill Quality Standards

All skills follow Claude's best practices:

- ✅ Gerund naming (verb+ing)
- ✅ Under 500 lines main file
- ✅ Progressive disclosure with reference files
- ✅ Project-specific patterns (not generic docs)
- ✅ Clear "when to use" triggers
- ✅ Real code examples from project

## Usage

Skills are automatically available to Claude Code when placed in `~/.claude/skills/`.

Claude will invoke skills based on:

- Task keywords matching skill description
- Project context and file types
- User explicit requests

## Next Steps

### Option A: Continue Building (Recommended)

Complete all 18 skills across 4 phases over ~4 weeks

### Option B: Test Current Skills

- Test with Haiku, Sonnet, Opus models
- Gather feedback on existing 4 skills
- Iterate before building more

### Option C: Prioritize by Usage

- Identify most frequently needed skills
- Build those first based on real usage patterns
- Add others as needed

## Testing

Each skill should be tested with:

1. **Haiku** - Ensure conciseness works with smaller model
2. **Sonnet** - Verify balanced performance
3. **Opus** - Confirm full capability usage

Create evaluation scenarios in `evaluations/` subdirectories.

## Contributing

When adding new skills:

1. Follow naming convention: `action-ing-target`
2. Include clear "when to use" section
3. Add reference files for complex topics
4. Test with all three Claude models
5. Update this README with skill details
