# Start App Script
# This script kills the process on port 8501 and starts the Streamlit app.

$ErrorActionPreference = "Stop"

try {
    # Set location to script directory
    $scriptPath = $MyInvocation.MyCommand.Path
    $scriptDir = Split-Path $scriptPath
    Set-Location $scriptDir

    $port = 8501
    Write-Host "Checking port $port..." -ForegroundColor Cyan

    # 1. Kill process on port 8501
    $proc = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1
    if ($proc) {
        Write-Host "Closing process $proc on port $port..." -ForegroundColor Yellow
        Stop-Process -Id $proc -Force
        Start-Sleep -Seconds 1
    }

    # 2. Start App
    if (Test-Path ".\venv\Scripts\Activate.ps1") {
        Write-Host "Starting application..." -ForegroundColor Green
        # Use call operator to run activation and then streamlit
        powershell -NoExit -Command "& { . .\venv\Scripts\Activate.ps1; python -m streamlit run app.py }"
    }
    else {
        Write-Host "Error: venv not found!" -ForegroundColor Red
        Read-Host "Press Enter to exit"
    }
}
catch {
    Write-Host "An error occurred: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "Press Enter to exit"
}
