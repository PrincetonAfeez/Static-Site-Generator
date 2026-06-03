Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "==> ruff check"
ruff check ssg tests

Write-Host "==> ruff format --check"
ruff format --check ssg tests

Write-Host "==> mypy"
mypy ssg
mypy tests --explicit-package-bases

Write-Host "==> pytest with coverage"
pytest --cov=ssg --cov-report=term-missing --cov-fail-under=97

Write-Host "All checks passed."
