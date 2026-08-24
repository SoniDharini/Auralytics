# Stop the Windows PostgreSQL service used by Auralytics.

$ErrorActionPreference = "Stop"
$ServiceName = "postgresql-x64-18"

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Host "PostgreSQL Windows service '$ServiceName' was not found." -ForegroundColor Red
    exit 1
}

if ($svc.Status -ne "Running") {
    Write-Host "PostgreSQL is already stopped." -ForegroundColor Yellow
    exit 0
}

Write-Host "Stopping PostgreSQL service '$ServiceName'..." -ForegroundColor Cyan
Stop-Service -Name $ServiceName
Write-Host "PostgreSQL stopped." -ForegroundColor Green
