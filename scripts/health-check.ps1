# LANDVILLA - backend/database/API health check wrapper.
# Run from the repository root while the backend is running:
#   powershell -ExecutionPolicy Bypass -File .\scripts\health-check.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\health-check.ps1 -Url http://192.168.1.20:8001
param([string]$Url = "http://localhost:8001", [switch]$SkipDb)
$root = Split-Path -Parent $PSScriptRoot
$py = "$root\backend\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Error "backend\.venv not found - run scripts\windows-setup.ps1 first"; exit 1 }
Push-Location "$root\backend"
$pyArgs = @("scripts\health_check.py", "--url", $Url)
if ($SkipDb) { $pyArgs += "--skip-db" }
# Optional: set $env:HEALTH_TOKEN to a session token first to also verify sign-in (not printed).
& $py @pyArgs
$code = $LASTEXITCODE
Pop-Location

# Android device reachability hint
if (Get-Command adb -ErrorAction SilentlyContinue) {
  $devices = (adb devices) -match "`tdevice$"
  if ($devices) { Write-Host "`nadb devices: $($devices.Count) connected" } else { Write-Host "`nadb: no device/emulator connected" }
}
exit $code
