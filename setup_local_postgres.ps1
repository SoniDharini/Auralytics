# One-time local Postgres bootstrap for Auralytics.
# Temporarily uses trust auth on localhost to set a known password, then restores scram-sha-256.
# Will re-launch itself via UAC if not already elevated.

$ErrorActionPreference = "Stop"
$ServiceName = "postgresql-x64-18"
$PgBin = Join-Path $env:USERPROFILE "PostgreSQL\18\bin"
$PgData = Join-Path $env:USERPROFILE "PostgreSQL\18\data"
$PgHba = Join-Path $PgData "pg_hba.conf"
$BackendEnv = Join-Path $PSScriptRoot "backend\.env"
$LocalPassword = "auralytics_local_dev"

function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($id)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdmin)) {
    Write-Host "Requesting Administrator permission (UAC)..." -ForegroundColor Yellow
    $args = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    try {
        Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $args -Wait
    } catch {
        Write-Host "UAC elevation was cancelled or failed." -ForegroundColor Red
        Write-Host "Open PowerShell as Administrator and run: .\setup_local_postgres.ps1" -ForegroundColor Yellow
        exit 1
    }
    exit $LASTEXITCODE
}

if (-not (Test-Path $PgHba)) {
    Write-Host "pg_hba.conf not found at $PgHba" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path "$PgBin\psql.exe")) {
    Write-Host "psql.exe not found at $PgBin" -ForegroundColor Red
    exit 1
}

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc -or $svc.Status -ne "Running") {
    Write-Host "Starting PostgreSQL service $ServiceName..." -ForegroundColor Cyan
    Start-Service -Name $ServiceName
    Start-Sleep -Seconds 2
}

$backup = "$PgHba.bak.auralytics"
Copy-Item $PgHba $backup -Force
Write-Host "Backed up pg_hba.conf -> $backup" -ForegroundColor Cyan

# Allow passwordless local TCP auth so we can ALTER USER.
$content = Get-Content $PgHba -Raw
$content = $content -replace '(?m)^(host\s+all\s+all\s+127\.0\.0\.1/32\s+)scram-sha-256\s*$', '${1}trust'
$content = $content -replace '(?m)^(host\s+all\s+all\s+::1/128\s+)scram-sha-256\s*$', '${1}trust'
$content = $content -replace '(?m)^(local\s+all\s+all\s+)scram-sha-256\s*$', '${1}trust'
Set-Content -Path $PgHba -Value $content -NoNewline

Write-Host "Reloading PostgreSQL with temporary trust auth..." -ForegroundColor Cyan
& "$PgBin\pg_ctl.exe" reload -D $PgData
if ($LASTEXITCODE -ne 0) {
    Write-Host "pg_ctl reload failed; restarting service..." -ForegroundColor Yellow
    Restart-Service -Name $ServiceName -Force
    Start-Sleep -Seconds 3
}

Write-Host "Setting local postgres password..." -ForegroundColor Cyan
$env:PGPASSWORD = $null
& "$PgBin\psql.exe" -h 127.0.0.1 -U postgres -d postgres -v ON_ERROR_STOP=1 -c "ALTER USER postgres WITH PASSWORD '$LocalPassword';"
if ($LASTEXITCODE -ne 0) {
    Copy-Item $backup $PgHba -Force
    & "$PgBin\pg_ctl.exe" reload -D $PgData | Out-Null
    Write-Host "Failed to ALTER USER postgres." -ForegroundColor Red
    exit 1
}

# Restore password auth.
Copy-Item $backup $PgHba -Force
& "$PgBin\pg_ctl.exe" reload -D $PgData | Out-Null
Write-Host "Restored scram-sha-256 auth." -ForegroundColor Green

if (-not (Test-Path $BackendEnv)) {
    Write-Host "backend\.env not found; create it from .env.example first." -ForegroundColor Red
    exit 1
}

$envText = Get-Content $BackendEnv -Raw
$newUrl = "DATABASE_URL=`"postgresql+asyncpg://postgres:$LocalPassword@localhost:5432/influenceos`""
if ($envText -match '(?m)^DATABASE_URL=.*$') {
    $envText = [regex]::Replace($envText, '(?m)^DATABASE_URL=.*$', $newUrl)
} else {
    $envText = "$newUrl`r`n$envText"
}
Set-Content -Path $BackendEnv -Value $envText -NoNewline
Write-Host "Updated backend\.env DATABASE_URL with the local password." -ForegroundColor Green
Write-Host ""
Write-Host "Done. Next (from backend\, with venv active):" -ForegroundColor Cyan
Write-Host "  python -m app.db.create_db"
Write-Host "  alembic upgrade head"
Write-Host "  uvicorn app.main:app --reload --port 8000"
Write-Host ""
Write-Host "Press Enter to close..."
[void][System.Console]::ReadLine()
