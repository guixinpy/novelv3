param(
  [switch]$RunE2E
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$VenvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"

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

if (-not (Test-Path $VenvPython)) {
  throw "Missing backend Windows venv. Run: powershell -ExecutionPolicy Bypass -File scripts/setup_windows.ps1"
}
if (-not (Test-Path (Join-Path $FrontendDir "node_modules\.bin\vitest.cmd"))) {
  throw "Missing frontend Windows dependencies. Run: powershell -ExecutionPolicy Bypass -File scripts/setup_windows.ps1"
}

$NpmExe = Resolve-Tool "npm.cmd" "npm"
$NodeExe = Resolve-Tool "node.exe" "node"

Write-Section "Backend pytest"
Push-Location $BackendDir
try {
  Invoke-Native $VenvPython @("-m", "pytest")
}
finally {
  Pop-Location
}

Write-Section "Frontend unit tests"
Push-Location $FrontendDir
try {
  Invoke-Native $NpmExe @("run", "test:unit")
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

Write-Section "Workspace perf smoke"
if ($env:PERF_SMOKE_BASE_URL -and $env:PERF_SMOKE_PROJECT_ID -and $env:PERF_SMOKE_SESSION) {
  Invoke-Native $NodeExe @(
    (Join-Path $RootDir "scripts\workspace_perf_smoke.mjs"),
    "--base-url", $env:PERF_SMOKE_BASE_URL,
    "--project-id", $env:PERF_SMOKE_PROJECT_ID,
    "--session", $env:PERF_SMOKE_SESSION
  )
}
else {
  Write-Host "Skipped: set PERF_SMOKE_BASE_URL, PERF_SMOKE_PROJECT_ID, and PERF_SMOKE_SESSION to enable."
}

Write-Section "Frontend E2E"
if ($RunE2E -or $env:RUN_E2E -eq "1") {
  & (Join-Path $ScriptDir "verify_frontend_e2e.ps1")
}
else {
  Write-Host "Skipped: pass -RunE2E or set RUN_E2E=1 to enable."
}
