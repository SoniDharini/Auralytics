# Stop Native PostgreSQL Server
$PG_DIR = "$PSScriptRoot\pgsql"
$DATA_DIR = "$PG_DIR\data"

Write-Host "Stopping native PostgreSQL server..." -ForegroundColor Yellow
& "$PG_DIR\bin\pg_ctl.exe" -D $DATA_DIR stop
Write-Host "PostgreSQL stopped." -ForegroundColor Yellow
