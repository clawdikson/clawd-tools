# API Test CLI (`apt`)

Lightning-fast API testing from terminal for developers who live in CLI.

## Overview

API Test CLI (`apt`) is a terminal-native HTTP client designed for rapid API testing during development. No GUI overhead, instant responses, persistent history, and preset management for common endpoints.

Perfect for CTOs and developers who need to:
- Test APIs during development without leaving terminal
- Save and reuse common API calls as presets  
- Track API testing history with timestamps
- Debug API responses with detailed timing information
- Manage authentication headers and request patterns

## Installation

The tool is installed as `api-test` with a system-wide `apt` command:

```bash
# Available immediately as apt from anywhere
apt get https://httpbin.org/get
```

## Quick Start

```bash
# Basic GET request
apt get https://api.github.com/user

# POST with JSON data
apt post https://httpbin.org/post -d '{"key":"value"}'

# With authentication header
apt get https://api.example.com -H "Authorization:Bearer your-token"

# Save frequently used request as preset
apt save github-user get https://api.github.com/user -H "Authorization:Bearer token"

# Run saved preset
apt preset github-user

# View request history
apt history 10
```

## Features

### 🚀 Fast HTTP Methods
- **GET, POST, PUT, PATCH, DELETE** - All standard HTTP methods
- **Color-coded output** - Visual status code indicators
- **Response timing** - See exact response times
- **Response size** - Track payload sizes
- **Error handling** - Clear error messages

### 📚 Preset Management
- **Save common requests** - `apt save name method url [options]`
- **Instant replay** - `apt preset name`
- **List all presets** - `apt list`
- **Include headers/data** - Save authentication and payload patterns

### 📜 Request History
- **Automatic logging** - All requests saved with NST timestamps
- **Recent requests** - `apt history [count]` shows last N requests
- **Full context** - Status, timing, size, errors recorded
- **Searchable** - Review past API interactions

### ⚙️ Configuration
- **Default headers** - Set common headers like Content-Type, Accept
- **Timeout control** - Global and per-request timeouts
- **Response formatting** - Pretty-print JSON responses
- **NST timezone** - All timestamps in Newfoundland time

## Command Reference

### Basic Usage
```bash
apt <method> <url> [options]
```

### HTTP Methods
```bash
apt get <url>          # GET request
apt post <url>         # POST request  
apt put <url>          # PUT request
apt patch <url>        # PATCH request
apt delete <url>       # DELETE request
```

### Options
```bash
-d, --data <json>      # Request body (JSON string or object)
-H, --header <h:v>     # Custom header (key:value, repeatable)
-t, --timeout <ms>     # Request timeout in milliseconds
--headers              # Show response headers in output
--no-pretty            # Disable JSON pretty printing
```

### Preset Management
```bash
apt save <name> <method> <url> [options]    # Save request as preset
apt preset <name>                          # Run saved preset
apt list                                   # List all saved presets
```

### History & Config
```bash
apt history [count]    # Show last N requests (default: 10)
apt config             # Show current configuration
apt help               # Show help information
```

## Example Workflows

### API Development Testing
```bash
# Test new endpoint during development
apt post https://localhost:3000/api/users -d '{"name":"John","email":"john@example.com"}'

# Save for repeated testing
apt save create-user post https://localhost:3000/api/users -d '{"name":"John","email":"john@example.com"}'

# Quick iteration testing
apt preset create-user
```

### Third-Party API Integration
```bash
# Test authentication
apt get https://api.stripe.com/v1/account -H "Authorization:Bearer sk_test_..."

# Save with auth for repeated use
apt save stripe-account get https://api.stripe.com/v1/account -H "Authorization:Bearer sk_test_..."

# Test different endpoints
apt preset stripe-account
apt get https://api.stripe.com/v1/customers -H "Authorization:Bearer sk_test_..."
```

### API Debugging
```bash
# Test with timing information
apt get https://slow-api.example.com/endpoint
# Output: Status: 200 | Time: 2.34s | Size: 1024 bytes

# Check recent failures
apt history 5
# Shows last 5 requests with status codes and errors

# Test timeout behavior  
apt get https://timeout-test.example.com -t 5000
```

## Configuration

Configuration is stored in `~/.api-test/config.json`:

```json
{
  "defaultHeaders": {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "api-test-cli/1.0"
  },
  "timeout": 10000,
  "followRedirects": true,
  "showHeaders": false,
  "prettyPrint": true
}
```

## File Structure

```
~/.api-test/
├── config.json    # Global configuration
├── presets.json   # Saved request presets
└── history.json   # Request history (last 100 requests)
```

## Why This Tool?

**Problem:** Testing APIs during development requires:
- Opening browser/Postman (context switch)
- Setting up requests repeatedly
- Losing testing history
- Slow feedback loops

**Solution:** Terminal-native API testing with:
- **2-second request cycle** vs 30+ seconds in GUI tools
- **Persistent presets** for common patterns
- **Automatic history** with NST timestamps
- **Zero context switching** from development environment

Perfect for CTO workflow where API testing happens constantly during:
- Debugging production issues
- Validating new endpoint behavior
- Testing third-party integrations
- Performance monitoring
- Authentication troubleshooting

## Integration with Other Tools

Works seamlessly with existing productivity tools:
- **`qn` (quick-note)** - Capture API insights: `qn "API rate limit: 1000/hour"`
- **`dl` (dev-learn)** - Log API learnings: `dl add "GraphQL subscriptions require WebSocket upgrade"`
- **`mn` (meeting-notes)** - Document API discussions during architecture reviews
- **`cu` (clickup)** - Create tasks from API testing results

## Performance

- **Lightweight** - Uses curl under the hood, minimal overhead
- **Fast startup** - Node.js CLI with optimized loading
- **Efficient storage** - JSON storage with automatic cleanup
- **NST timezone** - All timestamps in Newfoundland local time

Built for speed and developer experience. Perfect complement to terminal-based development workflow.

## Security

- **Local storage** - All data stays on your machine
- **No telemetry** - Zero external tracking or reporting
- **Secure headers** - Configuration supports API keys and tokens
- **History management** - Automatic cleanup of old requests (keeps last 100)

Authentication tokens are stored locally in presets and config. Use environment variables for sensitive data when possible.

---

*Fast, focused, and friction-free API testing for developers who live in the terminal.*