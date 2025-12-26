---
name: packaging-native-apps
description: Build and package Beena Native App using Briefcase for macOS, Windows, and Linux distribution. Covers pyproject.toml configuration, platform-specific dependencies, build automation, and troubleshooting packaging issues. Use when preparing releases or debugging build failures.
---

# Packaging Native Apps with Briefcase

Package the Beena Native App for cross-platform distribution using Briefcase. This skill covers the project's specific build setup, automation scripts, and platform-specific considerations.

## When to Use This Skill

- Preparing app releases for macOS/Windows/Linux
- Debugging build or packaging failures
- Adding platform-specific dependencies
- Updating app metadata or version numbers
- Troubleshooting bundled app runtime issues

## Quick Start Commands

```bash
# Development build (fast iteration)
briefcase dev

# Production build
briefcase build

# Package for distribution (macOS)
briefcase package --adhoc-sign

# Automated clean build (recommended)
python beenanativeapp/build_package.py
```

## Project Configuration

### pyproject.toml Structure

**Location**: `beenanativeapp/pyproject.toml`

```toml
[tool.briefcase]
project_name = "Beena"
bundle = "com.audiobeetechnologies"
version = "0.1.8"  # Update for each release
url = "https://hibeena.com"
console_app = false  # GUI app, not terminal

[tool.briefcase.app.beenanativeapp]
formal_name = "Beena"
icon = "resources/Beena"  # Icon set (must have .icns, .ico, .png)
sources = ["src/beenanativeapp"]
```

### Cross-Platform Dependencies

Dependencies in main `requires` list work on all platforms:

```toml
requires = [
    "fastapi>=0.110.0",
    "pydantic>=2.7.1",
    "playwright>=1.52.0",
    "toga>=0.5.1",
    "pandas>=2.0.0",
    # ... other deps
]
```

**Critical**: Playwright browser binaries are bundled automatically but require special handling (see troubleshooting section).

### Platform-Specific Dependencies

#### macOS

```toml
[tool.briefcase.app.beenanativeapp.macOS]
universal_build = true  # Supports both arm64 and x86_64
requires = [
    "std-nslog>=1.0.0",  # Capture stdout/stderr (required!)
    "desktop-notifier>=3.5.6",  # Native notifications
]
```

**Why std-nslog**: macOS sandboxing redirects stdout/stderr; this library captures them for logging.

#### Windows

```toml
[tool.briefcase.app.beenanativeapp.windows]
requires = [
    "pandas>=2.0.0",  # Sometimes needs explicit declaration
    "win10toast>=0.9",  # Windows toast notifications
]
```

**Note**: Windows requires `WindowsSelectorEventLoopPolicy` for asyncio (handled in app.py).

#### Linux

```toml
[tool.briefcase.app.beenanativeapp.linux]
requires = [
    # Add Linux-specific packages if needed
]

[tool.briefcase.app.beenanativeapp.linux.system.debian]
system_requires = [
    # System packages needed at build time
]
system_runtime_requires = [
    # System packages needed at runtime
]
```

## Build Automation Script

**Location**: `beenanativeapp/build_package.py`

This script automates the complete build process:

```python
#!/usr/bin/env python3
"""
Automated build script for Beena Native App.
Cleans previous builds and packages the app.
"""
import os
import shutil
import subprocess
import sys

def clean_build_dirs():
    """Remove previous build artifacts."""
    dirs_to_clean = ['build', 'dist']

    for dir_name in dirs_to_clean:
        dir_path = os.path.join('beenanativeapp', dir_name)
        if os.path.exists(dir_path):
            print(f"Cleaning {dir_path}...")
            shutil.rmtree(dir_path)

def build_and_package():
    """Run briefcase package with proper environment."""
    os.chdir('beenanativeapp')

    cmd = ['briefcase', 'package', '--adhoc-sign']

    result = subprocess.run(cmd, check=True)
    return result.returncode == 0

if __name__ == '__main__':
    clean_build_dirs()
    success = build_and_package()
    sys.exit(0 if success else 1)
```

**Usage**:

```bash
cd /Users/dikson/Work/automation/beena-native-app
python beenanativeapp/build_package.py
```

**Benefits**:

- Clean slate every build (no stale artifacts)
- Consistent environment setup
- Single command for complete build

## Build Workflow

### 1. Development Iteration

Fast iteration during development:

```bash
cd beenanativeapp

# Quick test run (no packaging)
briefcase dev

# OR run directly
cd ..
python -m beenanativeapp
```

**briefcase dev**:

- Doesn't create distributable package
- Faster than full build
- Good for UI testing
- Still uses Briefcase environment

### 2. Production Build

Create optimized build:

```bash
cd beenanativeapp
briefcase build
```

**Outputs**:

- `build/beenanativeapp/macos/app/` - Built app bundle (not signed)
- Build logs in terminal

### 3. Packaging for Distribution

#### macOS

```bash
# Ad-hoc signing (local distribution)
briefcase package --adhoc-sign

# Full signing (App Store or notarization)
briefcase package \
  --identity "Developer ID Application: Your Name (TEAM_ID)"

# Output: dist/Beena-0.1.8.dmg
```

**Ad-hoc signing**:

- Good for testing and internal distribution
- Won't pass Gatekeeper on other machines without user override
- Fast, no Apple Developer account needed

**Full signing**:

- Requires Apple Developer account
- Needed for public distribution
- Can be notarized for Gatekeeper approval

#### Windows

```bash
briefcase package

# Output: dist/Beena-0.1.8.msi
```

#### Linux

```bash
# AppImage (most portable)
briefcase package linux appimage

# Flatpak
briefcase package linux flatpak

# Snap
briefcase package linux snap
```

## Version Management

Update version before building:

1. **Update pyproject.toml**:

```toml
[tool.briefcase]
version = "0.1.9"  # Increment version
```

2. **Rebuild**:

```bash
python beenanativeapp/build_package.py
```

Version appears in:

- DMG/installer filename
- App "About" dialog
- System information

## Icon Requirements

**Location**: `beenanativeapp/resources/`

Required formats:

- `Beena.icns` - macOS (contains multiple sizes)
- `Beena.ico` - Windows (16x16 to 256x256)
- `Beena-96x96.png` - Linux
- `Beena.iconset/` - Source images for .icns generation

### Creating .icns from PNG

```bash
# Create iconset directory
mkdir Beena.iconset

# Copy PNGs at required sizes
cp icon_16x16.png Beena.iconset/icon_16x16.png
cp icon_32x32.png Beena.iconset/icon_32x32.png
# ... (16, 32, 64, 128, 256, 512, 1024)

# Generate .icns
iconutil -c icns Beena.iconset
```

## Troubleshooting

### Problem: Playwright browsers not found in bundled app

**Symptoms**:

```
Error: Executable doesn't exist at /path/to/.local-chromium/...
```

**Cause**: Playwright browsers not bundled or path resolution fails

**Solution**:

Add to `app.py` or `playwright_service.py`:

```python
from playwright._impl._driver import compute_driver_executable

# Get bundled Playwright path
driver_executable = compute_driver_executable()

# Launch with explicit path
browser = await playwright.chromium.launch(
    executable_path=driver_executable
)
```

**Project already implements this** in `services/playwright/browser_manager.py`.

### Problem: ImportError for dependencies

**Symptoms**:

```
ModuleNotFoundError: No module named 'xyz'
```

**Diagnosis**:

```bash
# Check if dependency is in pyproject.toml
grep "xyz" beenanativeapp/pyproject.toml

# Verify in built app
briefcase run
# Check terminal output for import errors
```

**Solution**:

Add missing dependency to `pyproject.toml`:

```toml
requires = [
    # ... existing deps
    "missing-package>=1.0.0",
]
```

Then rebuild:

```bash
briefcase build
```

### Problem: App crashes on startup (macOS)

**Diagnosis**:

```bash
# View crash logs
Console.app → User Reports → Beena crashes

# Or terminal output
briefcase run # Shows stdout/stderr
```

**Common causes**:

1. Missing `std-nslog` dependency
2. Thread/asyncio issues
3. Missing environment variables

**Solution for logging**:

Ensure `std-nslog` is in macOS requires:

```toml
[tool.briefcase.app.beenanativeapp.macOS]
requires = [
    "std-nslog>=1.0.0",
]
```

### Problem: Build fails with "No module named '\_sqlite3'"

**Cause**: Python built without SQLite support

**Solution**:

Briefcase should bundle SQLite. If not:

```bash
# macOS: Install Python with SQLite
brew reinstall python@3.11

# Verify
python -c "import sqlite3; print('OK')"

# Rebuild
python beenanativeapp/build_package.py
```

### Problem: Package size too large

**Diagnosis**:

```bash
# Check DMG size
ls -lh beenanativeapp/dist/Beena-*.dmg

# Inspect bundle contents
cd beenanativeapp/build/beenanativeapp/macos/app/Beena.app
du -sh Contents/*
```

**Common bloat**:

- Playwright browsers (~200MB)
- pandas with numpy (~100MB)
- Multiple Python versions in universal build

**Reduction strategies**:

1. Remove unused dependencies from pyproject.toml
2. Disable universal build (sacrifice M1/Intel compatibility):

```toml
[tool.briefcase.app.beenanativeapp.macOS]
universal_build = false
```

3. Use lighter alternatives (e.g., polars instead of pandas)

### Problem: Windows async errors

**Symptoms**:

```
RuntimeError: There is no current event loop in thread
```

**Solution**:

Already handled in `app.py`:

```python
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )
```

Verify this code runs before any async operations.

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build Beena

on:
  release:
    types: [created]

jobs:
  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install Briefcase
        run: pip install briefcase

      - name: Build app
        run: python beenanativeapp/build_package.py

      - name: Upload DMG
        uses: actions/upload-artifact@v3
        with:
          name: Beena-macOS
          path: beenanativeapp/dist/*.dmg
```

## Best Practices

1. **Clean builds for releases**: Always use `build_package.py` script
2. **Test on target platform**: Build and test on each OS before release
3. **Version consistently**: Update version in one place (pyproject.toml)
4. **Keep dependencies minimal**: Only include truly needed packages
5. **Test installation**: Install DMG/MSI on fresh machine to verify
6. **Monitor size**: Track package size; investigate sudden increases
7. **Document platform quirks**: Add comments for platform-specific workarounds

## Next Steps

- See `reference/platform-specific.md` for detailed platform notes
- Check `reference/signing-distribution.md` for code signing and notarization
- Review `reference/troubleshooting-builds.md` for comprehensive debugging guide
