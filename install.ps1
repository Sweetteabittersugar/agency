$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Agency v0.5.0 — source-only local install" -ForegroundColor Cyan
if (-not (Test-Path -LiteralPath ".venv")) {
    python -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install -e .
Write-Host "Installed. Start with:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\agency.exe start --project-root C:\path\to\project"
