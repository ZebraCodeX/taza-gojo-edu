# Shipping the Taza-Gojo EDU mobile apps

One React codebase → two store apps via **Capacitor** (`frontend/capacitor.config.json`).

```
frontend/src  ──► vite build ──► dist/  ──►  npx cap sync
                                            ├── android/  (Google Play .aab)
                                            └── ios/      (App Store .ipa/.xcarchive)
```

What is already prepared in the repo:

- `frontend/android/` — Gradle project (applicationId `edu.tazagojo.app`).
- `frontend/ios/` — Xcode project (bundle id `edu.tazagojo.app`).
- `frontend/resources/` — store-ready artwork:
  - `icon.png` (1024×1024, full-bleed) → all launcher icons + store icon
  - `splash.png` (2732×2732) → Android/iOS launch screens
  - `feature-graphic.png` (1024×500) → Google Play listing banner
- `frontend/public/icons/` — web/PWA icons (128/192/512/1024 PNG + SVG).

## Point the app at your production server

Web builds are same-origin (the Django app serves the SPA). Native builds are
never same-origin, so the API/WebSocket base URL is inlined at build time:

```bash
cd frontend
VITE_API_URL=https://taza-gojo-edu.fly.dev npm run build
npx cap sync
```

Everything else (auth, offline sync, WebRTC signaling) derives the correct URLs
from that one variable.

## Android → Google Play

1. Install Android Studio once, accept the SDK licenses:
   ```bash
   sdkmanager --licenses   # inside Android Studio / command-line-tools
   ```
2. Point signing + prod API URL:
   ```bash
   cd frontend
   VITE_API_URL=https://taza-gojo-edu.fly.dev npm run build
   npx cap sync android
   ```
3. Produce a Play-ready **AAB** (upload this file, never an APK except for
   internal testing / alpha):
   ```bash
   cd android
   ./gradlew bundleRelease
   ```
   `app/build/outputs/bundle/release/app-release.aab`
4. Google Play Console → Create app → set up the Play App Signing key →
   upload the AAB + `resources/feature-graphic.png` + screenshots →
   submit for review.

> First-time signing: create your keystore (`keytool -genkey -v -keystore
> release.keystore ...`) and put it in `android/app/`; `signingConfigs.release`
> in `app/build.gradle` already references `release.keystore`. This is YOURS
> alone — never commit it.

## iOS → App Store (requires a Mac with Xcode)

1. On the Mac, connect the repo (or copy `frontend/`):
   ```bash
   cd frontend
   VITE_API_URL=https://taza-gojo-edu.fly.dev npm run build
   npx cap sync ios
   npx cap open ios
   ```
2. In Xcode: set the Team (Signing & Capabilities), pick the bundle id
   `edu.tazagojo.app`.
3. Ensure privacy permissions: the app requests camera + microphone at runtime
   via `getUserMedia`; declare `NSCameraUsageDescription` /
   `NSMicrophoneUsageDescription` in `ios/App/App/Info.plist` if you hard-code
   them (Capacitor's default template includes the keys).
4. Archive (`Product → Archive`), then via **App Store Connect** upload the
   archive with Transporter or Organizer; complete the listing (icon is
   `resources/icon.png`, screenshots required, ≥ iPhone/iPad).

## How the native app differs from the web app

- **No service worker** — `services/offline.js` detects the Capacitor shell
  (`window.Capacitor.isNativePlatform`) and skips SW registration; the
  IndexedDB sync queue still works exactly the same, so offline progress → sync
  behaves identically.
- **HTTPS base URL** — `androidScheme: "https"` / `iosScheme: "capacitor"`; the
  API URL comes from `VITE_API_URL` (see above).
- **Cleartext blocked** — `android.allowMixedContent: false`; Apple rejects
  plain-HTTP traffic, so always point the app at the https fly.io URL.

## Store review checklist

- [ ] Screenshots: iPhone + Android (we can generate device frames from the
      video-call, gameplay and dashboard screens).
- [ ] Privacy policy URL — required by both stores (any static page works).
- [ ] Content rating questionnaire (no age-restricted content; fine for all).
- [ ] App icon with no transparent corners (`resources/icon.png` is ready).
- [ ] `io/App/App` bundle id matches App Store Connect; Play applicationId
      matches the console.
- [ ] Test build with `VITE_API_URL` pointing at the staging fly app before
      release.

## Regenerating platform assets after a redesign

```bash
# replace resources/icon.png (1024) + resources/splash.png (2732), then:
npx cap sync android
npx cap sync ios
```