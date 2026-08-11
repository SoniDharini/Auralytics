# Start Native PostgreSQL Server (No Docker required)
$PG_DIR = "$PSScriptRoot\pgsql"
$DATA_DIR = "$PG_DIR\data"
$LOG_FILE = "$PG_DIR\pg.log"

if (!(Test-Path $DATA_DIR)) {
    Write-Host "Initializing PostgreSQL cluster in $DATA_DIR..." -ForegroundColor Cyan
    & "$PG_DIR\bin\initdb.exe" -D $DATA_DIR -U postgres -A trust --encoding=UTF8
}

Write-Host "Starting native PostgreSQL server on port 5432..." -ForegroundColor Green
& "$PG_DIR\bin\pg_ctl.exe" -D $DATA_DIR -l $LOG_FILE start
Write-Host "PostgreSQL is running!" -ForegroundColor Green
