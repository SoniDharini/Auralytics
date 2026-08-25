# Stop PostgreSQL used by Auralytics (Standalone pgsql/ folder or Windows service).
$ErrorActionPreference = "Stop"

$PgCtl = Join-Path $PSScriptRoot "pgsql\bin\pg_ctl.exe"
$PgData = Join-Path $PSScriptRoot "pgsql\data"

if (Test-Path $PgCtl) {
    Write-Host "Stopping standalone PostgreSQL..." -ForegroundColor Cyan
    & $PgCtl stop -D $PgData -m fast | Out-Null
    Get-Process postgres -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "Standalone PostgreSQL stopped." -ForegroundColor Green
    exit 0
}

$ServiceName = "postgresql-x64-18"
$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    $svc = Get-Service *postgres* -ErrorAction SilentlyContinue | Select-Object -First 1
}

if ($svc -and $svc.Status -eq "Running") {
    Write-Host "Stopping PostgreSQL service '$($svc.Name)'..." -ForegroundColor Cyan
    Stop-Service -Name $svc.Name
    Write-Host "PostgreSQL service stopped." -ForegroundColor Green
    exit 0
}

Write-Host "PostgreSQL is not running." -ForegroundColor Yellow

