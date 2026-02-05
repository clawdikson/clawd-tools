# Reinstall core and healthsparq packages with latest changes
# Run from repo root: .\reinstall_packages.ps1
#
# Options:
#   -Sync    Also sync submodules to origin/master first
#   -All     Install all local packages (including sapphire)

param(
    [switch]$Sync,
    [switch]$All
)

$ErrorActionPreference = "Stop"

# Ensure we're in repo root
$RepoRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = Get-Location
}
Set-Location $RepoRoot

# Optionally sync submodules first
if ($Sync) {
    Write-Host "Syncing submodules first..." -ForegroundColor Yellow
    & "$RepoRoot\scripts\sync-submodules.ps1"
    Write-Host ""
}

Write-Host "=== Reinstalling Packages ===" -ForegroundColor Cyan

# Build package list
$packages = @("./core", "./healthsparq")
if ($All) {
    $packages += "./sapphire"
    $packages += "./output_generator"
}

# Install all packages in one command (faster)
$packageArgs = $packages | ForEach-Object { "-e"; $_ }
Write-Host "Installing: $($packages -join ', ')" -ForegroundColor Gray

uv pip install @packageArgs --force-reinstall --no-deps

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install packages" -ForegroundColor Red
    exit 1
}

Write-Host "`nPackages reinstalled successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Installed packages:" -ForegroundColor Gray
uv pip list | Select-String -Pattern "^(core|healthsparq|sapphire|output)"
