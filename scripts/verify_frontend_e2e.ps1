param(
  [int]$BackendPort = 0
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
$BackendHost = "127.0.0.1"
$BackendProcess = $null

function Write-Section {
  param([string]$Name)
  Write-Host ""
  Write-Host "== $Name =="
}

function Resolve-Tool {
  param(
    [string]$Name,
    [string]$DisplayName = $Name
  )

  $Command = Get-Command $Name -ErrorAction SilentlyContinue
  if (-not $Command) {
    throw "Missing command: $DisplayName"
  }
  return $Command.Source
}

function Invoke-Native {
  param(
    [string]$FilePath,
    [string[]]$Arguments
  )

  & $FilePath @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
  }
}

function Get-FreePort {
  $Listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse("127.0.0.1"), 0)
  try {
    $Listener.Start()
    return $Listener.LocalEndpoint.Port
  }
  finally {
    $Listener.Stop()
  }
}

function Convert-ToSqlitePath {
  param([string]$Path)
  return $Path.Replace("\", "/")
}

function Wait-ForHttp {
  param(
    [string]$Url,
    [int]$Attempts = 60
  )

  for ($i = 1; $i -le $Attempts; $i++) {
    try {
      Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2 | Out-Null
      return
    }
    catch {
      Start-Sleep -Seconds 1
    }
  }

  Write-Error "Timed out waiting for $Url"
}

if (-not (Test-Path $VenvPython)) {
  throw "Missing backend Windows venv. Run: powershell -ExecutionPolicy Bypass -File scripts/setup_windows.ps1"
}
if (-not (Test-Path (Join-Path $FrontendDir "node_modules\.bin\playwright.cmd"))) {
  throw "Missing frontend Windows dependencies. Run: powershell -ExecutionPolicy Bypass -File scripts/setup_windows.ps1"
}

$NpmExe = Resolve-Tool "npm.cmd" "npm"
$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("novelv3-e2e-" + [System.Guid]::NewGuid().ToString("N"))
$BackendLog = Join-Path $TempDir "backend.stdout.log"
$BackendErrorLog = Join-Path $TempDir "backend.stderr.log"
$DbPath = Join-Path $TempDir "mozhou.db"

if ($BackendPort -eq 0 -and $env:E2E_BACKEND_PORT) {
  $BackendPort = [int]$env:E2E_BACKEND_PORT
}
if ($BackendPort -eq 0) {
  $BackendPort = Get-FreePort
}

$BaseUrl = "http://${BackendHost}:${BackendPort}"
$env:E2E_BASE_URL = $BaseUrl
$env:MOZHOU_DATABASE_URL = "sqlite:///" + (Convert-ToSqlitePath $DbPath)
$env:MOZHOU_DISABLE_API_KEY = "1"
$env:PYTHON = $VenvPython

New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $RootDir ".tmp") | Out-Null

try {
  Write-Section "Alembic temporary database"
  Push-Location $BackendDir
  try {
    Invoke-Native $VenvPython @("-m", "alembic", "upgrade", "head")
  }
  finally {
    Pop-Location
  }

  Write-Section "Frontend build"
  Push-Location $FrontendDir
  try {
    Invoke-Native $NpmExe @("run", "build")
  }
  finally {
    Pop-Location
  }

  Write-Section "Start backend"
  $BackendProcess = Start-Process `
    -FilePath $VenvPython `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", $BackendHost, "--port", "$BackendPort") `
    -WorkingDirectory $BackendDir `
    -RedirectStandardOutput $BackendLog `
    -RedirectStandardError $BackendErrorLog `
    -WindowStyle Hidden `
    -PassThru

  Wait-ForHttp "$BaseUrl/api/v1/health"

  Write-Section "Playwright E2E"
  Push-Location $FrontendDir
  try {
    Invoke-Native $NpmExe @("run", "test:e2e")
  }
  finally {
    Pop-Location
  }
}
finally {
  if ($BackendProcess -and -not $BackendProcess.HasExited) {
    Stop-Process -Id $BackendProcess.Id -Force
    $BackendProcess.WaitForExit()
  }
  Remove-Item -LiteralPath $TempDir -Recurse -Force -ErrorAction SilentlyContinue
}
