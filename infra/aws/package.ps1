#Requires -Version 5.1
<#
.SYNOPSIS
  Build frontend and zip API + web artifacts for EC2 microservices (no Docker).
#>
$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Backend = Join-Path $RepoRoot "backend"
$Frontend = Join-Path $RepoRoot "frontend"
$BuildDir = Join-Path $PSScriptRoot "build"
$ApiStage = Join-Path $BuildDir "api-stage"
$WebStage = Join-Path $BuildDir "web-stage"
$ApiZip = Join-Path $BuildDir "api.zip"
$WebZip = Join-Path $BuildDir "web.zip"

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  throw "npm is required to build the frontend."
}

Write-Host "Building frontend..."
Push-Location $Frontend
try {
  if (Test-Path "package-lock.json") { npm ci } else { npm install }
  $env:VITE_API_URL = "/api/v1"
  npm run build
} finally {
  Pop-Location
}

if (Test-Path $BuildDir) { Remove-Item $BuildDir -Recurse -Force }
New-Item -ItemType Directory -Path $ApiStage | Out-Null
New-Item -ItemType Directory -Path $WebStage | Out-Null

$excludeDirNames = @(
  ".git", ".venv", "venv", "env", "__pycache__", ".pytest_cache", ".mypy_cache",
  ".ruff_cache", "htmlcov", "tests", "uploads", ".vscode", ".idea", "spa_dist",
  ".ebextensions", ".platform"
)

Get-ChildItem $Backend -Force | ForEach-Object {
  if ($excludeDirNames -contains $_.Name) { return }
  if ($_.Name -eq ".env") { return }
  Copy-Item $_.FullName (Join-Path $ApiStage $_.Name) -Recurse -Force
}
Get-ChildItem $ApiStage -Recurse -Directory -Filter "__pycache__" | Sort-Object FullName -Descending | ForEach-Object {
  Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
}

Copy-Item (Join-Path $Frontend "dist\*") $WebStage -Recurse -Force

Compress-Archive -Path (Join-Path $ApiStage "*") -DestinationPath $ApiZip -Force
Compress-Archive -Path (Join-Path $WebStage "*") -DestinationPath $WebZip -Force

Write-Host "Created $ApiZip"
Write-Host "Created $WebZip"
