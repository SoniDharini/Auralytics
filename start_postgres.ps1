# Start the Windows PostgreSQL service used by Auralytics (no Docker / no portable pgsql/).
# Install path expected: %USERPROFILE%\PostgreSQL\18  (service name: postgresql-x64-18)

$ErrorActionPreference = "Stop"
$ServiceName = "postgresql-x64-18"

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Host "PostgreSQL Windows service '$ServiceName' was not found." -ForegroundColor Red
    Write-Host "Install PostgreSQL 18, or update `$ServiceName in this script to match your install." -ForegroundColor Yellow
    exit 1
}

if ($svc.Status -eq "Running") {
    Write-Host "PostgreSQL is already running (service: $ServiceName, port 5432)." -ForegroundColor Green
    exit 0
}

Write-Host "Starting PostgreSQL service '$ServiceName'..." -ForegroundColor Cyan
Start-Service -Name $ServiceName
Start-Sleep -Seconds 2

$svc = Get-Service -Name $ServiceName
if ($svc.Status -eq "Running") {
    Write-Host "PostgreSQL is running!" -ForegroundColor Green
} else {
    Write-Host "Failed to start PostgreSQL. Status: $($svc.Status)" -ForegroundColor Red
    exit 1
}
