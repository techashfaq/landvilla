# LANDVILLA — Windows 10/11 Local Setup

## 1. Install tools (PowerShell as normal user)
```powershell
winget install Git.Git
winget install OpenJS.NodeJS.LTS            # Node 20+; dev used Node 24
winget install Python.Python.3.11
winget install MongoDB.Server               # MongoDB 7 Community (local dev DB)
winget install MongoDB.DatabaseTools        # mongodump / mongorestore
winget install Google.AndroidStudio
winget install Microsoft.VisualStudioCode
corepack enable                             # provides yarn 1.22.22 (package.json "packageManager")
```
In Android Studio, open **SDK Manager** and install: Android SDK Platform 36 and 37, Build-Tools 37.0.0,
NDK 27.1.12297006, CMake, Platform-Tools, and Android Emulator. Use JDK 17 or the bundled JBR
(*Settings → Build Tools → Gradle → Gradle JDK*).

Set the user environment variables (System Properties → Environment Variables):
```
ANDROID_HOME = %LOCALAPPDATA%\Android\Sdk
JAVA_HOME    = C:\Program Files\Android\Android Studio\jbr
Path        += %ANDROID_HOME%\platform-tools;%ANDROID_HOME%\emulator
```

## 2. Clone
```powershell
cd $HOME\source
git clone https://github.com/techashfaq/landvilla.git
cd landvilla
code .                                       # opens in VS Code
Set-ExecutionPolicy -Scope Process Bypass; .\scripts\windows-setup.ps1
```
Avoid very long paths. Paths like `C:\src\landvilla` reduce Gradle/NDK path-length errors.

## 3. Backend
```powershell
cd backend
.\.venv\Scripts\activate
notepad .env      # MONGO_URL=mongodb://localhost:27017, DB_NAME=landvilla_dev, SEED_DEMO_LISTINGS=true (dev only)
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```
Check it at http://localhost:8001/health and http://localhost:8001/api/meta. On first start the backend creates indexes and reference data (`seed.py`).

## 4. Frontend / Expo
```powershell
cd frontend
notepad .env      # EXPO_PUBLIC_BACKEND_URL (see table)
yarn start        # 'a' = open on Android emulator/device, 'w' = web
```
| Target | EXPO_PUBLIC_BACKEND_URL |
|---|---|
| Android emulator | `http://10.0.2.2:8001` |
| Physical phone (same Wi-Fi) | `http://<PC IPv4 from ipconfig>:8001` |
| Release build | `https://<your production API domain>` (HTTPS only) |

Allow the backend through the firewall (admin PowerShell, one time):
`New-NetFirewallRule -DisplayName "LANDVILLA API 8001" -Direction Inbound -LocalPort 8001 -Protocol TCP -Action Allow -Profile Private`

Android blocks plain `http://` in release builds. That is expected: release builds must use HTTPS.

## 5. Emulator & USB debugging
- **Emulator:** Android Studio → Device Manager → Create device (Pixel 8, API 36, Google Play image).
- **Phone:** Settings → About → tap *Build number* 7× → Developer options → USB debugging ON →
  connect USB → accept the prompt → `adb devices` should list the phone.
- `adb reverse tcp:8001 tcp:8001` lets a USB phone use `http://localhost:8001`.

## 6. Known limitations off-Emergent
- **Google sign-in** uses Emergent's managed auth (`auth.emergentagent.com`). It may not work against
  your local backend. For local testing of logged-in flows, set `SEED_TEST_SESSIONS=true` on your **dev**
  DB and use the test bearer tokens in `memory/test_credentials.md` (never in production).
- **Photo/document uploads** need Emergent storage credentials (`EMERGENT_LLM_KEY`). See HANDOVER_REPORT §F.

## 7. Troubleshooting
| Error | Fix |
|---|---|
| `yarn: command not found` | `corepack enable`, then reopen the terminal |
| `preinstall` cmd-guard error | Run `yarn install` (not npm) from `frontend/` |
| `SDK location not found` | Set `ANDROID_HOME` or `android\local.properties` → `sdk.dir=C:\\Users\\<you>\\AppData\\Local\\Android\\Sdk` |
| `Unsupported class file major version` | Gradle JDK must be 17 or JBR |
| Gradle "Filename longer than 260" | Clone to a short path. Enable long paths: `git config --system core.longpaths true` |
| Metro stale cache | `yarn start --clear` |
| `ECONNREFUSED` from app | Wrong backend URL (see table), backend not on 0.0.0.0, or firewall |
| `pip` fails on `emergentintegrations` | Use `requirements-local.txt` |
