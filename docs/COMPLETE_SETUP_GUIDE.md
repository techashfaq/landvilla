# LANDVILLA — Complete Setup Guide (zero → running on your Android phone)

The steps assume Windows 10/11, PowerShell, VS Code and Android Studio, with the repo cloned to `C:\src\landvilla`.
Skip any install step for a tool you already have. The config check (step 4) tells you what's missing.

## 0. What you are setting up
```
Android app (Expo, frontend/) ──HTTP(S) /api──▶ FastAPI backend (backend/server.py :8001) ──▶ MongoDB
        │                                              ├──▶ Emergent Object Storage   (photo/document uploads)
        └─▶ auth.emergentagent.com (Google sign-in) ───┴──▶ demobackend.emergentagent.com (session exchange)
                                                       └──▶ api.razorpay.com (featured orders; web client only)
Razorpay ──webhook──▶ https://<deployed backend>/api/payments/razorpay/webhook
```

## 1. Install tools (one time)
```powershell
winget install Git.Git
winget install OpenJS.NodeJS.LTS
winget install Python.Python.3.11
winget install MongoDB.Server; winget install MongoDB.Shell; winget install MongoDB.DatabaseTools
winget install Google.AndroidStudio
winget install Microsoft.VisualStudioCode
corepack enable          # yarn 1.22.22 – the repo's package manager (do NOT use npm install)
```
Close and reopen PowerShell. Then:
- Android Studio → More Actions → **SDK Manager**:
  - Install SDK Platforms 36 and 37.
  - On the *SDK Tools* tab, install Build-Tools 37.0.0, NDK 27.1.12297006, Platform-Tools and Emulator.
- Set the environment variables (Windows search: "Edit environment variables for your account"):
  - `ANDROID_HOME` = `C:\Users\<you>\AppData\Local\Android\Sdk`
  - `JAVA_HOME` = `C:\Program Files\Android\Android Studio\jbr`
  - Add to `Path`: `%ANDROID_HOME%\platform-tools` and `%ANDROID_HOME%\emulator`
- Install **Expo Go** from the Play Store on your phone. It must support **Expo SDK 58**.

## 2. Get the code
```powershell
mkdir C:\src -Force; cd C:\src
git clone -b dev https://github.com/techashfaq/landvilla.git
cd C:\src\landvilla
code .
```

## 3. Install dependencies and create env files
```powershell
cd C:\src\landvilla
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows-setup.ps1
```
This creates `backend\.venv`, installs `backend\requirements-local.txt`, runs `yarn install --frozen-lockfile`, and copies both `.env.example` files to `.env`.
Expected ending: `Done. Start backend: ...`

## 4. Edit configuration
`backend\.env` (development values):
```
MONGO_URL=mongodb://localhost:27017
DB_NAME=landvilla_dev
ADMIN_EMAILS=<your google email>
SEED_DEMO_LISTINGS=true
SEED_TEST_SESSIONS=true
```
Leave the Razorpay and Emergent lines as placeholders for now (see INTEGRATIONS_SETUP.md).

`frontend\.env`: pick **one** line from ANDROID_RUN_AND_DEBUG.md §2, for example `EXPO_PUBLIC_BACKEND_URL=http://10.0.2.2:8001` for the emulator.
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check-config.ps1     # expected: "Configuration OK"
```

## 5. Start the backend (window 1)
```powershell
cd C:\src\landvilla\backend
.\.venv\Scripts\activate
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```
Expected: `Seed report: inserted=...` and `Uvicorn running on http://0.0.0.0:8001`. Leave this window open.

## 6. Verify the backend and database (window 2)
```powershell
cd C:\src\landvilla
powershell -ExecutionPolicy Bypass -File .\scripts\health-check.ps1
```
Expected: every line `[PASS]` (the Razorpay and webhook lines may say "not set") and `RESULT: ALL REQUIRED CHECKS PASSED`.

## 7. Start the app (window 3)
```powershell
cd C:\src\landvilla\frontend
yarn start --clear
```
- **Emulator:** start it in Device Manager, then press `a`.
- **Phone via USB:** run `adb reverse tcp:8001 tcp:8001` and `adb reverse tcp:8081 tcp:8081`, then press `a`.
- **Phone on Wi-Fi:** scan the QR code with Expo Go.
- If Expo Go won't open the app, use a development build instead: `npx expo run:android` (the first build takes 10–20 minutes).

## 8. Test core features
1. The Home tab lists localities and listings (the demo ones are marked fictional). Open a listing.
2. Use search and filters (locality, type, price).
3. Sign in with Google. If it fails locally, this is a known limitation (INTEGRATIONS_SETUP §1). Test the logged-in APIs with test tokens instead (ANDROID_RUN_AND_DEBUG §5).
4. Once signed in: save a listing, send an enquiry, and post a listing (as owner).
   - Photo upload needs storage (INTEGRATIONS_SETUP §2).
5. As admin (your email in `ADMIN_EMAILS`): open Profile → Admin to see listings, brokers, reports and plans.

## 9. Next guides
ENVIRONMENT_VARIABLES.md · DATABASE_SETUP.md · ANDROID_RUN_AND_DEBUG.md · INTEGRATIONS_SETUP.md · ANDROID_BUILD_AND_PLAY.md · PRODUCTION_DEPLOYMENT.md · VERIFICATION_CHECKLIST.md
