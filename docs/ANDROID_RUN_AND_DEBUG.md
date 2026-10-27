# LANDVILLA — Run & Debug on Android

## 1. Which runtime to use
| Runtime | Works? | Notes |
|---|---|---|
| **Expo Go** (Play Store app) | **Likely, but not verified on your phone.** Every native module the app uses is part of the Expo SDK or the standard Expo Go set: webview, reanimated, worklets, gesture-handler, screens, safe-area, secure-store, image-picker, keyboard-controller, vector-icons. It has no custom native code | Fastest. **Your Expo Go app must support SDK 58** (Expo Go only runs one SDK at a time) |
| **Development build** (`npx expo run:android`) | Yes, once your Android SDK is set up | Use it if Expo Go fails, or to test the real package ID, icon and deep link `landvilla://` |
| **Release APK/AAB** | See ANDROID_BUILD_AND_PLAY.md | HTTPS backend required |

Google sign-in opens `auth.emergentagent.com` in the browser and returns to the app through a deep link:
`exp://…` in Expo Go, `landvilla://` in builds. Whether Emergent's auth accepts redirects from your own environment has **not been verified**.
If it fails, use test sessions on the dev DB (§5).

## 2. Networking: which URL to use
Inside Android, `localhost` means **the phone itself**, not your PC.

| Device | `EXPO_PUBLIC_BACKEND_URL` | Requirements |
|---|---|---|
| Android Studio emulator | `http://10.0.2.2:8001` | 10.0.2.2 is the emulator's alias for your PC |
| Phone via USB | `http://localhost:8001` | Run `adb reverse tcp:8001 tcp:8001` (and `adb reverse tcp:8081 tcp:8081` for Metro) after each reconnect |
| Phone on the same Wi-Fi | `http://192.168.x.y:8001` | Get the IP from `ipconfig` (IPv4 of your Wi-Fi adapter). Add a firewall rule for port 8001 and use a *Private* network profile |
| Any device to the deployed backend | `https://api.<your-domain>` | Valid TLS certificate |

The backend must listen on all interfaces: `uvicorn server:app --host 0.0.0.0 --port 8001`.
**Cleartext HTTP:** Expo Go and debug builds allow `http://`. **Release builds block it**, so they must use HTTPS.
**CORS** only matters for the web build. The backend currently allows `*`.
**API path:** the app calls `<EXPO_PUBLIC_BACKEND_URL>/api/...`. Health is at `/health` (no `/api`).

## 3. Start sequence (each in its own PowerShell window)
```powershell
# Window 1 – backend   (from C:\src\landvilla\backend)
.\.venv\Scripts\activate
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
# expected: "Seed report: inserted=..." then "Uvicorn running on http://0.0.0.0:8001"

# Window 2 – checks    (from C:\src\landvilla)
powershell -ExecutionPolicy Bypass -File .\scripts\check-config.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\health-check.ps1

# Window 3 – app       (from C:\src\landvilla\frontend)
yarn start --clear
# press  a  → opens on the running emulator / USB device in Expo Go
# or scan the QR code with Expo Go (phone on the same Wi-Fi)
# or development build:  npx expo run:android
```

## 4. Emulator setup
Android Studio → **Device Manager** → **+** → Pixel 8 → system image **API 36, Google Play** → Finish → ▶.
Check with `adb devices`; you should see `emulator-5554   device`.
Test the backend from inside the emulator: open Chrome in the emulator and go to `http://10.0.2.2:8001/health`. You should see `{"status":"ok"}`.

## 5. Physical phone (USB debugging)
1. On the phone, go to Settings → About phone → tap **Build number** 7 times → back → **Developer options** → **USB debugging** ON.
2. Connect the USB cable, choose the *File transfer* mode, and tap **Allow** on the "Allow USB debugging?" prompt.
3. Run `adb devices` and look for `<serial>   device`. If it says `unauthorized`, re-plug the phone and accept the prompt.
4. Run `adb reverse tcp:8001 tcp:8001` and `adb reverse tcp:8081 tcp:8081`.
5. Test the backend in the phone's Chrome at `http://localhost:8001/health` (USB) or `http://<PC-IP>:8001/health` (Wi-Fi).

**Signing in for local testing without Google** (dev DB only): set `SEED_TEST_SESSIONS=true` in `backend\.env` and restart the backend.
The app has no screen to paste a token, so test the logged-in APIs with PowerShell instead:
`Invoke-RestMethod http://localhost:8001/api/auth/me -Headers @{Authorization="Bearer test_session_buyer_landvilla"}`

## 6. Proof the app talks to the backend and the database
1. The Home tab shows Ujjain localities and listings. With `SEED_DEMO_LISTINGS=true` on the dev DB you'll see 20 demo listings marked "Demo Listing (Fictional)".
2. The backend window logs `GET /api/meta 200` and `GET /api/properties?... 200` **from your phone's IP**. That proves the round trip.
3. Change a locality name in mongosh, for example `db.localities.updateOne({slug:"nanakheda"},{$set:{name_en:"Nanakheda TEST"}})`, then pull to refresh in the app. The new name appears. Change it back afterwards.
4. Tap a listing. The detail page loads (`GET /api/properties/<id> 200`).

## 7. Troubleshooting
| Symptom | Likely cause | Diagnose | Fix |
|---|---|---|---|
| "Network request failed" | Wrong URL or localhost on the phone | Open the same URL in the phone's Chrome | Use the table in §2 and restart `yarn start --clear` |
| Works on the emulator, not on the phone | Firewall or a public network profile | `Test-NetConnection <PC-IP> -Port 8001` from another PC | Add the firewall rule and set the Wi-Fi to Private |
| Backend not reachable even on the PC | Not bound to 0.0.0.0 | `netstat -ano \| findstr 8001` | Restart with `--host 0.0.0.0` |
| Old backend URL still used | `EXPO_PUBLIC_*` is cached in the bundle | — | `yarn start --clear` |
| Expo Go says "incompatible SDK" | Expo Go version is not SDK 58 | Expo Go → Settings | Update Expo Go, or use `npx expo run:android` |
| `adb: device unauthorized` | Prompt not accepted | `adb devices` | Revoke USB authorisations in Developer options and re-plug |
| `adb` not recognised | PATH missing | `where adb` | Add `%LOCALAPPDATA%\Android\Sdk\platform-tools` to PATH |
| Google login returns to the app but you're not signed in | Emergent auth redirect not accepted off-Emergent | Backend log shows `POST /api/auth/session 401` | Use test sessions (dev) or migrate auth (INTEGRATIONS_SETUP §1) |
| Photo upload fails (500) | No `EMERGENT_LLM_KEY` or storage | Backend traceback mentions `_init_storage` | See INTEGRATIONS_SETUP §2 |
| Featured purchase shows "web only" | Intended: purchases are disabled in the native apps by design | — | Test payments in the web build (`yarn start`, then press `w`) |
| Metro "Unable to resolve module" | Dependencies are stale | — | `yarn install --frozen-lockfile`, then `yarn start --clear` |
| Gradle: SDK location / JDK errors | Environment | `echo $env:ANDROID_HOME` | See WINDOWS_SETUP.md §7 |
| Logs | — | `adb logcat *:E ReactNativeJS:V` · Metro window · Uvicorn window | — |
