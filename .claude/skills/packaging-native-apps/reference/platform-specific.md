# Platform-Specific Considerations

Detailed notes for packaging on macOS, Windows, and Linux.

## macOS Specifics

### Universal Builds

```toml
[tool.briefcase.app.beenanativeapp.macOS]
universal_build = true
```

**Benefits**:

- Single DMG works on both Apple Silicon (M1/M2) and Intel Macs
- Better user experience (automatic architecture detection)

**Trade-offs**:

- ~2x larger file size (includes both architectures)
- Slightly longer build time

**When to disable**:

- App only targets recent Macs (M1+ only)
- File size is critical concern
- Building for internal distribution only

### Signing & Notarization

#### Ad-hoc Signing (Development)

```bash
briefcase package --adhoc-sign
```

- Fast, no Apple Developer account needed
- Works on your machine immediately
- Won't pass Gatekeeper on other machines
- Users see "unidentified developer" warning

#### Developer ID Signing (Distribution)

```bash
briefcase package --identity "Developer ID Application: Name (TEAM_ID)"
```

**Requirements**:

- Active Apple Developer account ($99/year)
- Developer ID certificate installed

**Steps**:

1. Generate certificate in Apple Developer portal
2. Download and install in Keychain
3. Build with --identity flag

#### Notarization (Recommended)

```bash
# After packaging
xcrun notarytool submit dist/Beena-0.1.8.dmg \
  --keychain-profile "notary-profile" \
  --wait

# Staple notarization ticket
xcrun stapler staple dist/Beena-0.1.8.dmg
```

**Benefits**:

- No Gatekeeper warnings for users
- Professional distribution
- App Store submission ready

### macOS Logging with std-nslog

**Why needed**: macOS sandboxing redirects stdout/stderr to system log

```toml
[tool.briefcase.app.beenanativeapp.macOS]
requires = [
    "std-nslog>=1.0.0",
]
```

Without this, logging statements won't appear and debugging is impossible.

### Permissions

If app needs special permissions, add to Info.plist:

```xml
<key>NSCameraUsageDescription</key>
<string>App needs camera access for...</string>

<key>NSMicrophoneUsageDescription</key>
<string>App needs microphone for...</string>
```

Briefcase manages Info.plist automatically, but custom entries can be added via app configuration.

## Windows Specifics

### Async Event Loop

**Critical**: Windows requires specific event loop policy

```python
# In app.py, before any async code
import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )
```

Without this, async operations will fail with cryptic errors.

### Windows Dependencies

Some packages behave differently on Windows:

```toml
[tool.briefcase.app.beenanativeapp.windows]
requires = [
    "pandas>=2.0.0",  # Sometimes needs explicit declaration
    "win10toast>=0.9",  # Windows notifications
]
```

### Installer (MSI)

```bash
briefcase package windows

# Output: dist/Beena-0.1.8.msi
```

**MSI format**:

- Professional installer experience
- Add/Remove Programs integration
- Per-user or per-machine installation
- Upgrade/uninstall support

### Windows Defender

Windows Defender may flag packaged app on first run:

**Solutions**:

1. Sign with authenticode certificate
2. Build reputation over time
3. Submit to Microsoft for analysis

## Linux Specifics

### Multiple Formats

```bash
# AppImage (most portable)
briefcase package linux appimage

# Flatpak (sandboxed, modern)
briefcase package linux flatpak

# Snap (Ubuntu ecosystem)
briefcase package linux snap
```

**Recommendations**:

- **AppImage**: Best for widest compatibility
- **Flatpak**: Modern, sandboxed, growing adoption
- **Snap**: If targeting Ubuntu primarily

### AppImage Details

**Benefits**:

- No installation needed
- Works on most distributions
- Single-file distribution

**Limitations**:

- No automatic updates
- Manual desktop integration
- Larger file size

### System Dependencies

For Debian/Ubuntu:

```toml
[tool.briefcase.app.beenanativeapp.linux.system.debian]
system_requires = [
    "libgtk-3-dev",
    "libwebkit2gtk-4.0-dev",
]
system_runtime_requires = [
    "libgtk-3-0",
    "libwebkit2gtk-4.0-37",
]
```

**system_requires**: Needed at build time
**system_runtime_requires**: Needed when running app

### Desktop Integration

AppImage needs manual desktop integration:

```bash
# After download
chmod +x Beena-0.1.8.AppImage

# Optional: Create desktop entry
./Beena-0.1.8.AppImage --appimage-extract-and-run
```

## Cross-Platform Testing

### Virtual Machines

**macOS**: Can only build on Mac hardware or macOS VM
**Windows**: Use Parallels, VMware, or VirtualBox
**Linux**: VirtualBox or Docker containers

### CI/CD Matrix

```yaml
strategy:
  matrix:
    os: [macos-latest, windows-latest, ubuntu-latest]
    python-version: ["3.11"]
```

### Platform-Specific Code

Use platform detection:

```python
import sys

if sys.platform == 'darwin':
    # macOS-specific code
    pass
elif sys.platform == 'win32':
    # Windows-specific code
    pass
elif sys.platform.startswith('linux'):
    # Linux-specific code
    pass
```

## File Paths

### Cross-Platform Path Handling

```python
from pathlib import Path

# Always use Path for cross-platform compatibility
config_dir = Path.home() / '.beena'
config_file = config_dir / 'config.json'

# NOT platform-independent:
# config_file = os.path.expanduser('~/.beena/config.json')  # Unix-only
```

### Application Data Directories

```python
import appdirs

# Cross-platform app data
user_data_dir = appdirs.user_data_dir('Beena', 'AudioBee')
user_config_dir = appdirs.user_config_dir('Beena', 'AudioBee')

# On macOS: ~/Library/Application Support/Beena/
# On Windows: C:\Users\<name>\AppData\Local\AudioBee\Beena\
# On Linux: ~/.local/share/Beena/
```

## Resource Bundling

### Icons

**Required for each platform**:

```
resources/
├── Beena.icns        # macOS (512x512@2x, 256x256@2x, etc.)
├── Beena.ico         # Windows (16, 32, 48, 256)
├── Beena-96x96.png   # Linux
└── Beena.iconset/    # Source for .icns
```

### Assets

Bundle assets in app package:

```python
from pathlib import Path
import sys

if getattr(sys, 'frozen', False):
    # Running as bundled app
    bundle_dir = Path(sys._MEIPASS)
else:
    # Running as script
    bundle_dir = Path(__file__).parent

asset_path = bundle_dir / 'resources' / 'logo.png'
```

## Performance Considerations

### Startup Time

**macOS**:

- Universal builds slower to start (load both architectures metadata)
- Notarized apps slightly slower (check ticket)

**Windows**:

- Defender scanning adds startup delay
- MSI installation caches help subsequent runs

**Linux**:

- AppImage mounts filesystem (slight delay)
- Flatpak sandboxing adds overhead

### File Size

**Typical sizes for Beena app**:

- macOS DMG (universal): ~350MB
- Windows MSI: ~280MB
- Linux AppImage: ~300MB

**Major contributors**:

- Python runtime: ~50MB
- Playwright browsers: ~200MB
- pandas + numpy: ~100MB
- Toga + dependencies: ~30MB

## Troubleshooting Platform-Specific Issues

### macOS: App won't open

```bash
# Check Gatekeeper status
spctl --assess --verbose Beena.app

# Disable Gatekeeper temporarily (testing only)
sudo spctl --master-disable

# View system log
log show --predicate 'process == "Beena"' --last 5m
```

### Windows: MSI installation fails

```bash
# Enable MSI logging
msiexec /i Beena-0.1.8.msi /l*v install.log

# Check log for errors
notepad install.log
```

### Linux: Missing libraries

```bash
# Check dependencies
ldd Beena.AppImage

# Install missing libraries
sudo apt install <missing-lib>
```
