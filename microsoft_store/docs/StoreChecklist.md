# Microsoft Store Submission Checklist

Use this checklist before uploading KALKI.msix to Partner Center.

## Build Verification

- [ ] `build.ps1` completed without errors
- [ ] All 4 PyInstaller targets present in `app/dist/`:
  - [ ] `KALKI/`
  - [ ] `KALKI_Server/`
  - [ ] `KALKI_Listener/`
  - [ ] `KALKI_Setup_Wizard/`
- [ ] `package.ps1` completed — `KALKI.msix` generated
- [ ] `validate.ps1` passed all checks

## Manifest (AppxManifest.xml)

- [ ] `Identity Name` matches Partner Center value
- [ ] `Identity Publisher` matches Partner Center value (exact CN=...)
- [ ] `PublisherDisplayName` matches Partner Center value
- [ ] `Version` is updated (format: X.X.X.0)
- [ ] `ProcessorArchitecture` is `x64`

## Visual Assets

- [ ] StoreLogo.png (50x50)
- [ ] Square44x44Logo.png (44x44)
- [ ] Square71x71Logo.png (71x71)
- [ ] Square150x150Logo.png (150x150)
- [ ] Wide310x150Logo.png (310x150)
- [ ] SplashScreen.png (620x300)
- [ ] Target size variants for Square44x44Logo

## Store Listing (Partner Center)

- [ ] App description written (min 200 chars)
- [ ] At least 1 screenshot uploaded (1366x768 or similar)
- [ ] Category selected (Productivity or Utilities)
- [ ] Age rating questionnaire completed
- [ ] Privacy policy URL provided (can link to GitHub TERMS.md)
- [ ] Pricing set (Free, or your chosen price tier)

## Functional Verification

- [ ] `store_build.txt` is present in the package
- [ ] Auto-updater is disabled in Store build
- [ ] KALKI launches correctly from MSIX install
- [ ] Voice commands work (microphone permission requested)
- [ ] TTS audio plays correctly (Edge-TTS SSL bypass active)

## Final Steps

- [ ] Upload `microsoft_store/output/KALKI.msix` to Partner Center
- [ ] Fill in all required Store listing fields
- [ ] Submit for certification review
- [ ] Expected review time: 1-3 business days
