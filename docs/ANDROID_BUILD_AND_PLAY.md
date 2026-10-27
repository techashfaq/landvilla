# LANDVILLA — Android Studio Build & Company Play Console Release

## 1. Project type (verified)
- **Expo managed workflow with Continuous Native Generation (CNG).** No `android/` folder exists in the repo, so Android
  Studio cannot open the repo directly. You generate the native project locally with `expo prebuild`.
- No native customisations exist (no `android/`, no config plugins of your own), so prebuild is safe and repeatable.
- A test prebuild was run in a throwaway copy on 2026 (`npx expo prebuild --platform android --no-install`). It **succeeded**.
  The values below come from that output. **No APK/AAB was built in the Emergent workspace** because it has no Android SDK/JDK.

| Item | Value (verified from generated project) |
|---|---|
| Application ID / namespace | `com.emergent.ujjainestate.rq35d7` (from `app.json`) |
| App label | LANDVILLA |
| versionName / versionCode | `1.0.0` / `1` (app.json has no `android.versionCode`) ⚠ |
| minSdk / targetSdk / compileSdk | 24 / 36 / 37 |
| Build-Tools / NDK | 37.0.0 / 27.1.12297006 |
| Gradle / AGP / Kotlin | Gradle 9.4.1 wrapper / AGP 9.2.1 / Kotlin 2.2.0 |
| JDK | 17 (Android Studio bundled JBR) |
| Icon / adaptive icon / splash | `assets/images/icon.png`, `adaptive-icon.png` (bg #000000), `splash-image.png` |
| Permissions in final manifest | INTERNET, VIBRATE. CAMERA, RECORD_AUDIO, READ_MEDIA_*, READ/WRITE_EXTERNAL_STORAGE and SYSTEM_ALERT_WINDOW are **removed** (`tools:node="remove"`). Photos use the system photo picker |
| Release signing in generated template | **debug keystore**. You must configure your own upload key (step 4) |

⚠ **Version mismatch:** Emergent generated build 1.0.1, but `app.json` says `1.0.0` and has no versionCode. Play Console
rejects a versionCode that is not higher than one already uploaded. Before your first company build, set the values in
`frontend/app.json` → `expo.version` (for example `"1.0.2"`) and `expo.android.versionCode` (higher than any code already uploaded).

⚠ **Package name decision:** `com.emergent.ujjainestate.rq35d7` contains "emergent". The package name is permanent once an app is
published. If the 1.0.1 build was **never uploaded** to any Play account, consider changing `android.package` to something like
`com.<yourcompany>.landvilla` before your first upload. Check that it is unused, because Play rejects duplicates.

## 2. Generate the Android project & open in Android Studio
```powershell
cd landvilla\frontend
yarn install --frozen-lockfile
npx expo prebuild --platform android      # creates frontend\android (git-ignored)
```
Android Studio → **Open** → select `landvilla\frontend\android` (not the repo root) → let Gradle sync.
Re-run `npx expo prebuild --platform android --clean` after changing `app.json` or adding native packages.
`--clean` regenerates the folder, so keep the keystore and `keystore.properties` **outside** `android\` (see below).

## 3. Debug build
```powershell
# backend running on :8001, emulator started or phone connected (adb devices)
npx expo run:android                      # builds debug APK, installs, starts Metro
# or from Android Studio: Run ▶ (variant: debug)
```
Debug APK: `frontend\android\app\build\outputs\apk\debug\app-debug.apk`

## 4. Upload key (on YOUR machine only — never commit, never share in chat)
```powershell
mkdir $HOME\landvilla-signing
keytool -genkeypair -v -storetype PKCS12 -keystore $HOME\landvilla-signing\upload.jks `
  -alias landvilla-upload -keyalg RSA -keysize 2048 -validity 10000
```
Store the keystore and passwords in your company password manager, and keep an offline backup.
Create `$HOME\landvilla-signing\keystore.properties`:
```
storeFile=C:/Users/<you>/landvilla-signing/upload.jks
storePassword=<in password manager>
keyAlias=landvilla-upload
keyPassword=<in password manager>
```
After every prebuild, edit `frontend\android\app\build.gradle`:
```gradle
def ksProps = new Properties()
def ksFile = file("${System.getProperty('user.home')}/landvilla-signing/keystore.properties")
if (ksFile.exists()) ksProps.load(new FileInputStream(ksFile))
android {
  signingConfigs {
    release {
      storeFile ksProps['storeFile'] ? file(ksProps['storeFile']) : null
      storePassword ksProps['storePassword']; keyAlias ksProps['keyAlias']; keyPassword ksProps['keyPassword']
    }
  }
  buildTypes { release { signingConfig signingConfigs.release /* replace signingConfigs.debug */ } }
}
```

## 5. Release AAB
```powershell
cd frontend
# set production URL for the release bundle (HTTPS):
Set-Content .env "EXPO_PUBLIC_BACKEND_URL=https://<your production API domain>"
cd android
.\gradlew.bat clean bundleRelease
```
Output: `frontend\android\app\build\outputs\bundle\release\app-release.aab`

Verify:
```powershell
jarsigner -verify -verbose -certs app\build\outputs\bundle\release\app-release.aab | Select-String "jar verified"
keytool -printcert -jarfile app\build\outputs\bundle\release\app-release.aab   # must show YOUR upload cert, not "Android Debug"
# test the exact bundle on a device with bundletool:
java -jar bundletool.jar build-apks --bundle=app\build\outputs\bundle\release\app-release.aab --output=lv.apks --connected-device --ks=$HOME\landvilla-signing\upload.jks --ks-key-alias=landvilla-upload
java -jar bundletool.jar install-apks --apks=lv.apks
```
Release sanity check: the app must load listings from the production URL, sign-in must work, and no test or demo data may appear.

## 6. Company Play Console checklist
| Item | Status |
|---|---|
| Application ID unique / final | **Your decision** (see ⚠ above) |
| Play App Signing (Google holds app key, you hold upload key) | Enable at first upload. Your action |
| Target SDK ≥ current Play requirement | targetSdk 36 (verified in prebuild). Check the current rule in Play Console |
| AAB format | Use step 5 |
| Icon 512×512, feature graphic 1024×500, ≥2 phone screenshots | Your action (current icon is from the app assets. Check quality and branding) |
| Privacy policy URL | `https://<prod-domain>/api/legal/privacy` exists, **but the text is marked DRAFT**. Get legal review |
| Account deletion URL (public, no login) | `https://<prod-domain>/api/legal/delete-account` exists. In-app delete is in Profile |
| Data Safety | Collected: name, email, profile photo (Google), phone (optional, shared only with consent), photos, broker documents, approximate locality, messages. Payments go through Razorpay (web only). Data is encrypted in transit (HTTPS) and deletion is available. Your declaration |
| Content rating / target audience | Questionnaire. Adults 18+ recommended (property transactions) |
| Permissions / photo picker | No broad media permissions (verified in manifest) |
| UGC: report, block, moderation | Implemented (report listing/user, block, admin reports & listing moderation) |
| In-app payments policy | Featured purchases are **disabled in the Android/iOS apps** (server returns 403 unless the client is web), so the apps do not sell digital goods outside Play Billing. Keep it that way, or review the policy before enabling |
| Closed testing | New **personal** developer accounts need 12+ testers for 14 days. **Organisation** accounts are usually exempt. Check in your console |
| Pre-launch report | Review after the first internal/closed upload |
| Reviewer access | Google sign-in only. Give reviewers a dedicated Google test account in *App access*, never production admin credentials |
| Release notes / staged rollout | Start at 10–20% in production |

Nothing has been uploaded, submitted or published.
