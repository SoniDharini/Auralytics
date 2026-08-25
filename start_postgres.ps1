# Start PostgreSQL used by Auralytics (Standalone pgsql/ folder or Windows service).
$ErrorActionPreference = "Stop"

function Test-PortOpen ([string]$Server, [int]$Port) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $async = $tcp.BeginConnect($Server, $Port, $null, $null)
        $wait = $async.AsyncWaitHandle.WaitOne(1000, $false)
        if (-not $wait) {
            $tcp.Close()
            return $false
        }
        $tcp.EndConnect($async)
        $tcp.Close()
        return $true
    } catch {
        return $false
    }
}

if (Test-PortOpen "127.0.0.1" 5432) {
    Write-Host "PostgreSQL is already running on port 5432!" -ForegroundColor Green
    exit 0
}

$PgBin  = Join-Path $PSScriptRoot "pgsql\bin"
$PgData = Join-Path $PSScriptRoot "pgsql\data"

if (Test-Path "$PgBin\postgres.exe") {
    Write-Host "Found standalone PostgreSQL in pgsql/..." -ForegroundColor Cyan
    $pidFile = Join-Path $PgData "postmaster.pid"
    if (Test-Path $pidFile) {
        $pidContent = Get-Content $pidFile -ErrorAction SilentlyContinue
        if ($pidContent -and $pidContent.Count -ge 1) {
            $oldPid = [int]($pidContent[0].Trim())
            $proc = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
            if (-not $proc) {
                Write-Host "Removing stale postmaster.pid (PID $oldPid)..." -ForegroundColor Yellow
                Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
            }
        }
    }

    Write-Host "Starting standalone PostgreSQL..." -ForegroundColor Cyan
    $cmdLine = "`"$PgBin\postgres.exe`" -D `"$PgData`""
    $null = wmic process call create $cmdLine

    $started = $false
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Milliseconds 500
        if (Test-PortOpen "127.0.0.1" 5432) {
            $started = $true
            break
        }
    }

    if ($started) {
        Write-Host "Standalone PostgreSQL is running on port 5432!" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "Failed to verify PostgreSQL on port 5432." -ForegroundColor Red
        exit 1
    }
}

# Fallback to Windows Service check
$ServiceName = "postgresql-x64-18"
$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    $svc = Get-Service *postgres* -ErrorAction SilentlyContinue | Select-Object -First 1
}

if (-not $svc) {
    Write-Host "PostgreSQL was not found in pgsql/ directory and no Windows service was found." -ForegroundColor Red
    Write-Host "Ensure pgsql/ exists or PostgreSQL service is installed." -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting PostgreSQL service '$($svc.Name)'..." -ForegroundColor Cyan
Start-Service -Name $svc.Name
Start-Sleep -Seconds 2

if ((Get-Service -Name $svc.Name).Status -eq "Running") {
    Write-Host "PostgreSQL service is running!" -ForegroundColor Green
} else {
    Write-Host "Failed to start PostgreSQL service." -ForegroundColor Red
    exit 1
}



