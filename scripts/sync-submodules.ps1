# Sync all submodules to their remote master branches
# Run from repo root: .\scripts\sync-submodules.ps1
#
# This script handles the common "commits don't follow merge-base" conflict
# by resetting submodules to origin/master.

param(
    [switch]$Force,  # Reset even if there are local changes
    [switch]$Pull    # Also pull the main repo first
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "=== Submodule Sync Script ===" -ForegroundColor Cyan
Write-Host "Repo root: $RepoRoot" -ForegroundColor Gray

Set-Location $RepoRoot

# Optionally pull main repo first
if ($Pull) {
    Write-Host "`nPulling main repository..." -ForegroundColor Yellow
    git fetch origin
    
    # Check if we're in a merge conflict state
    $mergeHead = Test-Path ".git\MERGE_HEAD"
    if ($mergeHead) {
        Write-Host "Merge in progress, will resolve submodule conflicts..." -ForegroundColor Yellow
    }
}

# List of submodules to sync
$submodules = @("core", "healthsparq", "sapphire", "output_generator")

foreach ($submodule in $submodules) {
    $submodulePath = Join-Path $RepoRoot $submodule
    
    if (-not (Test-Path $submodulePath)) {
        Write-Host "`n[$submodule] Not found, skipping..." -ForegroundColor Gray
        continue
    }
    
    Write-Host "`n[$submodule] Syncing..." -ForegroundColor Cyan
    
    Set-Location $submodulePath
    
    # Check for local changes
    $status = git status --porcelain
    if ($status -and -not $Force) {
        Write-Host "  WARNING: Local changes detected. Use -Force to override." -ForegroundColor Yellow
        Write-Host "  $status" -ForegroundColor Gray
        Set-Location $RepoRoot
        continue
    }
    
    # Fetch and reset to origin/master
    Write-Host "  Fetching origin..." -ForegroundColor Gray
    git fetch origin
    
    Write-Host "  Resetting to origin/master..." -ForegroundColor Gray
    git reset --hard origin/master
    
    $currentCommit = git rev-parse --short HEAD
    Write-Host "  Now at: $currentCommit" -ForegroundColor Green
    
    Set-Location $RepoRoot
}

# Stage all submodule changes
Write-Host "`nStaging submodule updates..." -ForegroundColor Yellow
foreach ($submodule in $submodules) {
    if (Test-Path $submodule) {
        git add $submodule 2>$null
    }
}

# Check if we need to complete a merge
$mergeHead = Test-Path ".git\MERGE_HEAD"
if ($mergeHead) {
    Write-Host "`nCompleting merge..." -ForegroundColor Yellow
    
    # Stage any other conflicted files (accept theirs for non-submodule conflicts)
    $conflicts = git diff --name-only --diff-filter=U
    if ($conflicts) {
        Write-Host "  Resolving file conflicts..." -ForegroundColor Gray
        foreach ($file in $conflicts) {
            if ($file -notin $submodules) {
                git checkout --theirs $file 2>$null
                git add $file
            }
        }
    }
    
    # Complete the merge
    git commit -m "chore: merge remote changes and sync submodules"
    Write-Host "Merge completed!" -ForegroundColor Green
}

Write-Host "`n=== Sync Complete ===" -ForegroundColor Cyan
git status --short

Write-Host "`nTo reinstall packages, run:" -ForegroundColor Gray
Write-Host "  uv pip install -e ./core -e ./healthsparq --force-reinstall --no-deps" -ForegroundColor White

