# LANDVILLA - safe Windows bootstrap (no secrets, nothing deleted, nothing deployed).
# Run from the repository root in PowerShell:
#   Set-ExecutionPolicy -Scope Process Bypass; .\scripts\windows-setup.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

function Need($cmd, $hint) {
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { Write-Warning "$cmd not found -> $hint"; return $false }
  Write-Host "OK  $cmd" -ForegroundColor Green; return $true
}

$ok = $true
$ok = (Need git    "winget install Git.Git") -and $ok
$ok = (Need node   "winget install OpenJS.NodeJS.LTS") -and $ok
$ok = (Need python "winget install Python.Python.3.11") -and $ok
if (-not (Get-Command yarn -ErrorAction SilentlyContinue)) { Write-Host "Enabling corepack for yarn..."; corepack enable }
Need mongod    "Install MongoDB Community 7 (or use Atlas)" | Out-Null
Need mongodump "Install MongoDB Database Tools (needed only for backups)" | Out-Null
if (-not $env:ANDROID_HOME) { Write-Warning "ANDROID_HOME not set (e.g. $env:LOCALAPPDATA\Android\Sdk) - needed for Android builds" }
if (-not $ok) { Write-Error "Install the missing tools above and re-run."; exit 1 }

# Backend
Push-Location "$root\backend"
if (-not (Test-Path ".venv")) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\pip.exe install -r requirements-local.txt
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env"; Write-Host "Created backend\.env from example - edit it." }
Pop-Location

# Frontend
Push-Location "$root\frontend"
yarn install --frozen-lockfile
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env"; Write-Host "Created frontend\.env from example - edit it." }
Pop-Location

Write-Host "`nDone. Start backend:  cd backend; .\.venv\Scripts\activate; uvicorn server:app --host 0.0.0.0 --port 8001 --reload"
Write-Host "Start app:            cd frontend; yarn start   (press 'a' for Android)"
