# Reinstall core and healthsparq packages with latest changes
# Run from repo root: .\reinstall_packages.ps1

Write-Host "Reinstalling core package..." -ForegroundColor Cyan
Set-Location core
python -m pip install -e . --force-reinstall --no-deps
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install core package" -ForegroundColor Red
    exit 1
}
Set-Location ..

Write-Host "`nReinstalling healthsparq package..." -ForegroundColor Cyan
Set-Location healthsparq
python -m pip install -e . --force-reinstall --no-deps
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install healthsparq package" -ForegroundColor Red
    exit 1
}
Set-Location ..

Write-Host "`nPackages reinstalled successfully!" -ForegroundColor Green
Write-Host "Now run: python audiobee_wellmark/test.py --limit 10"

