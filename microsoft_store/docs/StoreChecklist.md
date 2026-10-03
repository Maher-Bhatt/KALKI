# Microsoft Store Submission Checklist

Use this checklist before uploading KALKI.msix to Partner Center.

## Build Verification

- [x] `build.ps1` completed without errors
- [x] All 4 PyInstaller targets present in `app/dist/`:
  - [x] `KALKI/`
  - [x] `KALKI_Server/`
  - [x] `KALKI_Listener/`
  - [x] `KALKI_Setup_Wizard/`
- [x] `package.ps1` completed — `KALKI.msix` generated
- [x] `validate.ps1` passed all checks

## Manifest (AppxManifest.xml)

- [x] `Identity Name` matches Partner Center value
- [x] `Identity Publisher` matches Partner Center value (exact CN=...)
- [x] `PublisherDisplayName` matches Partner Center value
- [x] `Version` is updated (format: X.X.X.0)
- [x] `ProcessorArchitecture` is `x64`

## Visual Assets

- [x] StoreLogo.png (50x50)
- [x] Square44x44Logo.png (44x44)
- [x] Square71x71Logo.png (71x71)
- [x] Square150x150Logo.png (150x150)
- [x] Wide310x150Logo.png (310x150)
- [x] SplashScreen.png (620x300)
- [x] Target size variants for Square44x44Logo

## Store Listing (Partner Center)

- [ ] App description written (min 200 chars)
- [ ] At least 1 screenshot uploaded (1366x768 or similar)
- [ ] Category selected (Productivity or Utilities)
- [ ] Age rating questionnaire completed
- [ ] Privacy policy URL provided (can link to GitHub TERMS.md)
- [ ] Pricing set (Free, or your chosen price tier)

## Functional Verification

- [x] `store_build.txt` is present in the package
- [x] Auto-updater is disabled in Store build
- [x] KALKI launches correctly from MSIX install
- [x] Voice commands work (microphone permission requested)
- [x] TTS audio plays correctly (Edge-TTS SSL bypass active)

## Final Steps

- [ ] Upload `microsoft_store/output/KALKI.msix` to Partner Center
- [ ] Fill in all required Store listing fields
- [ ] Submit for certification review
- [ ] Expected review time: 1-3 business days
