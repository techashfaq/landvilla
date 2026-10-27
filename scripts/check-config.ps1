# LANDVILLA - configuration check (read-only). Prints names/status only, never secret values.
# Run from the repository root:  powershell -ExecutionPolicy Bypass -File .\scripts\check-config.ps1
$root = Split-Path -Parent $PSScriptRoot
$fail = 0
function Pass($m) { Write-Host "[PASS] $m" -ForegroundColor Green }
function Warn($m) { Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Fail($m) { Write-Host "[FAIL] $m" -ForegroundColor Red; $script:fail++ }

function ReadEnv($path) {
  $h = @{}
  if (Test-Path $path) {
    Get-Content $path | Where-Object { $_ -match '^\s*[A-Za-z_][A-Za-z0-9_]*\s*=' } | ForEach-Object {
      $k, $v = $_ -split '=', 2; $h[$k.Trim()] = $v.Trim().Trim('"')
    }
  }
  return $h
}

# --- tools
foreach ($t in @(@("git","--version"), @("node","--version"), @("python","--version"), @("yarn","--version"))) {
  $c = Get-Command $t[0] -ErrorAction SilentlyContinue
  if ($c) { Pass "$($t[0]) $(& $t[0] $t[1] 2>&1 | Select-Object -First 1)" } else { Fail "$($t[0]) not installed" }
}
if (Get-Command adb -ErrorAction SilentlyContinue) { Pass "adb found" } else { Warn "adb not on PATH (add %ANDROID_HOME%\platform-tools)" }
if ($env:ANDROID_HOME) { Pass "ANDROID_HOME set" } else { Warn "ANDROID_HOME not set (only needed for emulator/native builds)" }
$nodeMajor = [int]((node --version) -replace 'v(\d+)\..*','$1')
if ($nodeMajor -lt 20) { Fail "Node $nodeMajor is too old; install Node 20 LTS or newer" }

# --- backend env
$be = ReadEnv "$root\backend\.env"
if ($be.Count -eq 0) { Fail "backend\.env missing - copy backend\.env.example" } else {
  foreach ($k in "MONGO_URL","DB_NAME") { if ($be[$k]) { Pass "backend $k set" } else { Fail "backend $k empty" } }
  foreach ($k in "RAZORPAY_KEY_ID","RAZORPAY_KEY_SECRET","RAZORPAY_WEBHOOK_SECRET","ADMIN_EMAILS","PUBLIC_BASE_URL") {
    if ($be[$k] -and $be[$k] -notmatch 'replace_with|xxxx|example') { Pass "backend $k set" } else { Warn "backend $k not set (optional for local dev)" }
  }
  if ($be["RAZORPAY_KEY_ID"] -like "rzp_live_*") { Warn "RAZORPAY_KEY_ID is a LIVE key - use rzp_test_ keys for development" }
  foreach ($k in "SEED_DEMO_LISTINGS","SEED_TEST_SESSIONS") { Write-Host "       $k = $($be[$k])  (must be false in production)" }
}
if (Test-Path "$root\backend\.venv\Scripts\python.exe") { Pass "backend venv exists" } else { Warn "backend\.venv missing - run scripts\windows-setup.ps1" }

# --- frontend env
$fe = ReadEnv "$root\frontend\.env"
if (-not $fe["EXPO_PUBLIC_BACKEND_URL"]) { Fail "frontend\.env EXPO_PUBLIC_BACKEND_URL missing" } else {
  $u = $fe["EXPO_PUBLIC_BACKEND_URL"]
  Pass "EXPO_PUBLIC_BACKEND_URL = $u"   # public value, safe to print
  if ($u -match '/api/?$') { Fail "EXPO_PUBLIC_BACKEND_URL must NOT end with /api (the app appends it)" }
  if ($u -match 'localhost|127\.0\.0\.1') { Warn "localhost only works with 'adb reverse tcp:8001 tcp:8001' or web; emulator uses 10.0.2.2" }
  if ($u -match 'preview\.emergentagent\.com') { Warn "points to the Emergent preview backend, not your local backend" }
}
$secretLike = $fe.Keys | Where-Object { $_ -like "EXPO_PUBLIC_*" -and $_ -match 'SECRET|PASSWORD|PRIVATE|MONGO|KEY_SECRET' }
if ($secretLike) { Fail "secret-looking EXPO_PUBLIC_ variables found: $secretLike (these are bundled into the APK)" } else { Pass "no secrets in EXPO_PUBLIC_ variables" }
if (Test-Path "$root\frontend\node_modules") { Pass "frontend node_modules installed" } else { Warn "run: cd frontend; yarn install --frozen-lockfile" }

# --- git hygiene
Push-Location $root
$tracked = git ls-files 2>$null | Select-String -Pattern '(^|/)\.env$|\.jks$|\.keystore$|google-services\.json|service-account|test_credentials'
if ($tracked) { Fail "sensitive files tracked by git: $tracked" } else { Pass "no .env/keystore/credential files tracked by git" }
Pop-Location

Write-Host ""
if ($fail -gt 0) { Write-Host "$fail check(s) FAILED" -ForegroundColor Red; exit 1 } else { Write-Host "Configuration OK" -ForegroundColor Green }
