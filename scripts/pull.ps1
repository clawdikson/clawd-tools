# Pull repository and sync all submodules
# Run from repo root: .\scripts\pull.ps1
#
# This script handles the common submodule conflicts automatically.

param(
    [switch]$Reinstall  # Also reinstall packages after pull
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "=== Git Pull with Submodules ===" -ForegroundColor Cyan

# Step 1: Fetch everything
Write-Host "`n[1/4] Fetching all remotes..." -ForegroundColor Yellow
git fetch --all --recurse-submodules

# Step 2: Update submodules to remote first (prevents conflicts)
Write-Host "`n[2/4] Updating submodules to origin/master..." -ForegroundColor Yellow
$submodules = @("core", "healthsparq", "sapphire", "output_generator")

foreach ($sub in $submodules) {
    if (Test-Path $sub) {
        Push-Location $sub
        git fetch origin 2>$null
        git reset --hard origin/master 2>$null
        $commit = git rev-parse --short HEAD
        Write-Host "  $sub -> $commit" -ForegroundColor Gray
        Pop-Location
    }
}

# Step 3: Pull main repo (should be clean now)
Write-Host "`n[3/4] Pulling main repository..." -ForegroundColor Yellow
git pull --no-recurse-submodules

if ($LASTEXITCODE -ne 0) {
    # If pull failed, we might have a merge in progress
    $mergeHead = Test-Path ".git\MERGE_HEAD"
    if ($mergeHead) {
        Write-Host "  Resolving merge..." -ForegroundColor Yellow
        
        # Stage submodules
        foreach ($sub in $submodules) {
            if (Test-Path $sub) {
                git add $sub 2>$null
            }
        }
        
        # Check for remaining conflicts
        $conflicts = git diff --name-only --diff-filter=U 2>$null
        if ($conflicts) {
            Write-Host "  Remaining conflicts:" -ForegroundColor Red
            Write-Host "  $conflicts" -ForegroundColor Red
            Write-Host "`n  Please resolve manually, then run:" -ForegroundColor Yellow
            Write-Host "  git add <files>" -ForegroundColor White
            Write-Host "  git commit" -ForegroundColor White
            exit 1
        }
        
        # Complete merge
        git commit -m "chore: merge remote changes"
        Write-Host "  Merge completed!" -ForegroundColor Green
    } else {
        Write-Host "  Pull failed!" -ForegroundColor Red
        exit 1
    }
}

# Step 4: Final submodule sync (in case pull updated pointers)
Write-Host "`n[4/4] Final submodule sync..." -ForegroundColor Yellow
git submodule update --init --recursive

Write-Host "`n=== Pull Complete ===" -ForegroundColor Green
git log --oneline -3
Write-Host ""

# Optionally reinstall packages
if ($Reinstall) {
    Write-Host "Reinstalling packages..." -ForegroundColor Yellow
    uv pip install -e ./core -e ./healthsparq --force-reinstall --no-deps
}

Write-Host "`nDone! To reinstall packages:" -ForegroundColor Gray
Write-Host "  .\reinstall_packages.ps1" -ForegroundColor White

