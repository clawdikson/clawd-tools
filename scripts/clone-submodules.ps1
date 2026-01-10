#
# Clone submodules helper script (Windows PowerShell)
# Dynamically parses .gitmodules and clones/updates submodules
#
# Usage:
#   .\scripts\clone-submodules.ps1          # Standard submodule init/update
#   .\scripts\clone-submodules.ps1 -Fresh   # Fresh clone (removes existing)
#   .\scripts\clone-submodules.ps1 -Shallow # Shallow clone (faster)
#   .\scripts\clone-submodules.ps1 -Standalone # Clone as separate repos (not submodules)
#

param(
    [switch]$Fresh,
    [switch]$Shallow,
    [switch]$Standalone,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$GitModules = Join-Path $RootDir ".gitmodules"

# Colors for output
function Write-Success { param($Message) Write-Host $Message -ForegroundColor Green }
function Write-Warning { param($Message) Write-Host $Message -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host $Message -ForegroundColor Red }

if ($Help) {
    Write-Host "Usage: .\clone-submodules.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Fresh       Remove existing submodule dirs before cloning"
    Write-Host "  -Shallow     Use shallow clones (depth=1) for faster setup"
    Write-Host "  -Standalone  Clone as separate git repos instead of submodules"
    Write-Host "  -Help        Show this help message"
    exit 0
}

# Check .gitmodules exists
if (-not (Test-Path $GitModules)) {
    Write-Error "Error: .gitmodules not found at $GitModules"
    exit 1
}

# Parse .gitmodules dynamically
# Returns: hashtable with path and url
function Parse-GitModules {
    $submodules = @()
    $currentPath = ""
    $currentUrl = ""

    Get-Content $GitModules | ForEach-Object {
        $line = $_.Trim()

        if ($line -match '^path\s*=\s*(.+)$') {
            $currentPath = $Matches[1].Trim()
        }
        elseif ($line -match '^url\s*=\s*(.+)$') {
            $currentUrl = $Matches[1].Trim()
        }

        # Output when we have both path and url
        if ($currentPath -and $currentUrl) {
            $submodules += @{
                Path = $currentPath
                Url  = $currentUrl
            }
            $currentPath = ""
            $currentUrl = ""
        }
    }

    return $submodules
}

# Change to root directory
Push-Location $RootDir

try {
    $submodules = Parse-GitModules
    $submoduleCount = $submodules.Count

    Write-Success "Found $submoduleCount submodules in .gitmodules"
    Write-Host ""

    foreach ($submodule in $submodules) {
        $path = $submodule.Path
        $url = $submodule.Url
        $fullPath = Join-Path $RootDir $path

        Write-Warning "Processing: $path"
        Write-Host "  URL: $url"

        # Handle fresh clone
        if ($Fresh -and (Test-Path $fullPath)) {
            Write-Host "  Removing existing directory..."
            Remove-Item -Recurse -Force $fullPath
        }

        if ($Standalone) {
            # Clone as separate repository
            $gitDir = Join-Path $fullPath ".git"

            if (Test-Path $gitDir) {
                Write-Success "  Already exists, pulling latest..."
                Push-Location $fullPath
                try {
                    git pull --rebase
                }
                finally {
                    Pop-Location
                }
            }
            elseif (Test-Path $fullPath) {
                Write-Warning "  Directory exists but not a git repo, skipping"
            }
            else {
                Write-Host "  Cloning as standalone repo..."
                if ($Shallow) {
                    git clone --depth 1 $url $path
                }
                else {
                    git clone $url $path
                }
            }
        }
        else {
            # Use git submodule commands
            if ($Shallow) {
                Write-Host "  Initializing with shallow clone..."
                git submodule update --init --depth 1 $path
            }
            else {
                Write-Host "  Initializing submodule..."
                git submodule update --init $path
            }
        }

        # Verify
        if (Test-Path $fullPath) {
            Write-Success "  OK"
        }
        else {
            Write-Error "  FAILED"
        }
        Write-Host ""
    }

    Write-Success "Done!"

    # Show status
    Write-Host ""
    Write-Host "Submodule status:"
    git submodule status
}
finally {
    Pop-Location
}
