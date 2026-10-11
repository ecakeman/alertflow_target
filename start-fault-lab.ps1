<#
.SYNOPSIS
  One-click launcher for Fault Lab (backend + console).

.DESCRIPTION
  Prepares a Python virtualenv and the frontend build if needed, then starts the
  simulator. In production mode (default) the backend serves the built console on
  http://localhost:<Port>/. In -Dev mode the Vite dev server is used (port 5173).

  Messages are in English on purpose so the script renders correctly in both
  Windows PowerShell 5.1 and PowerShell 7.

.EXAMPLE
  .\start-fault-lab.ps1
  .\start-fault-lab.ps1 -Port 9000 -ControlToken my-secret -NoBrowser
  .\start-fault-lab.ps1 -Dev
#>
[CmdletBinding()]
param(
    [int]$Port = 8090,
    [string]$ControlToken,
    [string]$DiagnosticsToken,
    [string]$LogLevel = 'info',
    [switch]$Dev,          # run the Vite dev server instead of the built console
    [switch]$NoBuild,      # skip building the frontend
    [switch]$NoBrowser,    # do not open a browser
    [switch]$Reinstall     # recreate the virtualenv / reinstall frontend deps
)

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot

function Write-Step([string]$msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Warn([string]$msg) { Write-Host "!! $msg" -ForegroundColor Yellow }
function Write-Ok([string]$msg)   { Write-Host "   $msg" -ForegroundColor Green }

function New-RandomToken {
    -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
}

function Open-BrowserLater([string]$url, [int]$seconds) {
    if ($NoBrowser) { return }
    Start-Job -ScriptBlock {
        param($u, $s)
        Start-Sleep -Seconds $s
        Start-Process $u
    } -ArgumentList $url, $seconds | Out-Null
}

# --- 0. resolve the control token -------------------------------------------
if (-not $ControlToken) { $ControlToken = $env:SIMULATOR_CONTROL_TOKEN }
if (-not $ControlToken) {
    $ControlToken = New-RandomToken
    Write-Warn "No control token given; generated a random one (shown below)."
}

# --- 1. backend virtualenv ---------------------------------------------------
Write-Step "Preparing backend environment"
$VenvDir = Join-Path $Root '.venv'
$VenvPy = Join-Path $VenvDir 'Scripts\python.exe'

if ($Reinstall -and (Test-Path $VenvDir)) { Remove-Item -Recurse -Force $VenvDir }

if (-not (Test-Path $VenvPy)) {
    $baseCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $baseCmd) { $baseCmd = Get-Command py -ErrorAction SilentlyContinue }
    if (-not $baseCmd) { throw "python not found. Install Python 3.10+ and add it to PATH." }
    Write-Ok "Creating virtualenv .venv"
    & $baseCmd.Source -m venv $VenvDir
    Write-Ok "Installing backend dependencies"
    & $VenvPy -m pip install --upgrade pip | Out-Null
    & $VenvPy -m pip install -e "$Root[dev]"
    if ($LASTEXITCODE -ne 0) { throw "Backend dependency install failed." }
} else {
    Write-Ok "Reusing existing virtualenv .venv"
}

# --- 2. frontend -------------------------------------------------------------
$Frontend = Join-Path $Root 'frontend'
$Dist = Join-Path $Frontend 'dist'
$NodeModules = Join-Path $Frontend 'node_modules'
$NeedNpm = (-not (Test-Path $NodeModules)) -or $Reinstall

if ($Dev -or (-not $NoBuild)) {
    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $npm) {
        if ($Dev) { throw "npm not found; -Dev mode needs Node.js." }
        Write-Warn "npm not found; skipping frontend build. Root path will show a build hint page."
    } else {
        Push-Location $Frontend
        try {
            if ($NeedNpm) {
                Write-Step "Installing frontend dependencies"
                if (Test-Path (Join-Path $Frontend 'package-lock.json')) { npm ci } else { npm install }
                if ($LASTEXITCODE -ne 0) { throw "Frontend dependency install failed." }
            }
            if (-not $Dev) {
                if ($Reinstall -or (-not (Test-Path (Join-Path $Dist 'index.html')))) {
                    Write-Step "Building the console"
                    npm run build
                    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
                } else {
                    Write-Ok "Reusing existing build frontend/dist"
                }
            }
        } finally { Pop-Location }
    }
}

# --- 3. environment ----------------------------------------------------------
$env:SIMULATOR_ADDR = ":$Port"
$env:SIMULATOR_CONTROL_TOKEN = $ControlToken
$env:SIMULATOR_CONFIG_PATH = (Join-Path $Root 'config\simulator.json')
$env:SIMULATOR_LOG_LEVEL = $LogLevel
$env:PYTHONPATH = (Join-Path $Root 'backend')
if ($DiagnosticsToken) {
    $env:SIMULATOR_DIAGNOSTICS_TOKEN = $DiagnosticsToken
} else {
    Remove-Item Env:\SIMULATOR_DIAGNOSTICS_TOKEN -ErrorAction SilentlyContinue
}

# --- 4. banner ---------------------------------------------------------------
$consoleUrl = if ($Dev) { 'http://localhost:5173/' } else { "http://localhost:$Port/" }
Write-Host ""
Write-Host "----------------------------------------------" -ForegroundColor DarkGray
Write-Host " Fault Lab starting" -ForegroundColor White
Write-Host "   Console        $consoleUrl"
Write-Host "   Liveness       http://localhost:$Port/healthz"
Write-Host "   Control token  $ControlToken" -ForegroundColor Yellow
if ($DiagnosticsToken) { Write-Host "   Diagnostics    $DiagnosticsToken" -ForegroundColor Yellow }
Write-Host " Paste the control token into the console sign-in panel."
Write-Host " Press Ctrl+C to stop."
Write-Host "----------------------------------------------" -ForegroundColor DarkGray

# --- 5. run ------------------------------------------------------------------
if ($Dev) {
    Write-Step "Starting backend (background) and Vite dev server (foreground)"
    # The job process inherits the environment variables set above.
    $job = Start-Job -ScriptBlock {
        param($py, $root)
        Set-Location $root
        & $py -m fault_lab.main
    } -ArgumentList $VenvPy, $Root
    Start-Sleep -Seconds 2
    Open-BrowserLater 'http://localhost:5173/' 5
    try {
        Push-Location $Frontend
        npm run dev
    } finally {
        Pop-Location
        Write-Step "Stopping backend"
        Stop-Job $job -ErrorAction SilentlyContinue
        Remove-Job $job -Force -ErrorAction SilentlyContinue
    }
} else {
    Open-BrowserLater $consoleUrl 3
    Write-Step "Starting Fault Lab backend (foreground)"
    Push-Location $Root
    try {
        & $VenvPy -m fault_lab.main
    } finally { Pop-Location }
}
