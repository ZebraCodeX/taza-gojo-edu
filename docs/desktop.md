# Desktop app (Tauri)

A thin native shell around the same React build, for school computer labs and
teachers' laptops. [Tauri](https://tauri.app) produces small binaries (a few MB)
using the OS webview.

## Prerequisites

- Rust (`rustup`) and the Tauri system dependencies for your OS
  (<https://tauri.app/start/prerequisites/>)
- Node 20+

## Run

```bash
cd frontend
npm install
npx tauri dev      # live-reload desktop window
npx tauri build    # native installers in src-tauri/target/release/bundle
```

## Icons

The bundle expects icons in `src-tauri/icons/`. Generate them from the existing
app icon:

```bash
cd frontend
npx tauri icon public/icons/icon-512.png
```

## How it fits

`src-tauri/tauri.conf.json` points `frontendDist` at `../dist` (the same build
the PWA uses) and `beforeBuildCommand` at `npm run build`. No app code changes
are needed — the desktop shell loads the identical UI.

## Native builds for phones

The Android and iOS shells are already in `frontend/android` and `frontend/ios`
(Capacitor). See `docs/STORE-DEPLOY.md`.
