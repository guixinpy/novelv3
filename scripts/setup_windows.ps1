param(
  [string]$Python = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$BackendVenv = Join-Path $BackendDir ".venv"

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

$PythonExe = $Python
if (-not $PythonExe) {
  $PythonExe = $env:PYTHON
}
if (-not $PythonExe) {
  $PythonExe = (Resolve-Tool "python" "python")
}

$NpmExe = Resolve-Tool "npm.cmd" "npm"

Write-Section "Backend venv"
Invoke-Native $PythonExe @("--version")
Invoke-Native $PythonExe @("-m", "venv", "--clear", $BackendVenv)

$VenvPython = Join-Path $BackendVenv "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
  throw "Failed to create Windows backend venv: $VenvPython"
}

Invoke-Native $VenvPython @("-m", "pip", "install", "-r", (Join-Path $BackendDir "requirements.txt"))

Write-Section "Frontend dependencies"
Push-Location $FrontendDir
try {
  Invoke-Native $NpmExe @("ci")
}
finally {
  Pop-Location
}

Write-Host ""
Write-Host "Windows setup complete."
