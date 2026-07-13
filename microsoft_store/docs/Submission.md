# Microsoft Store Submission Guide

Step-by-step instructions for submitting KALKI to the Microsoft Store.

---

## 1. Build the MSIX Package

```powershell
cd "C:\Users\maher\Music\KALKI application"
powershell -ExecutionPolicy Bypass -File microsoft_store\build_msix.ps1
```

The output file will be at: `microsoft_store/output/KALKI.msix`

---

## 2. Open Partner Center

Go to: https://partner.microsoft.com/en-us/dashboard/home

Navigate to: **Apps and games** → **Kalki** → **Start submission**

---

## 3. Fill in Submission Details

### Packages
- Click **Packages** in the left sidebar
- Drag and drop `microsoft_store/output/KALKI.msix`
- Wait for upload and validation to complete

### Store Listing
- **Product name**: Kalki
- **Description**: (Use the text below)

```
KALKI is your intelligent AI desktop assistant for Windows.

Features:
- Voice-controlled AI assistant with natural language understanding
- Neural text-to-speech with Microsoft Edge voices
- Spotify integration (play, pause, skip, search)
- Google Calendar and Gmail integration
- Cybersecurity tools (port scanning, WHOIS, Shodan)
- Smart home automation and system control
- Code generation and analysis
- Weather, news, and real-time information
- Auto-start on Windows boot with system tray icon
- Beautiful dark-themed web UI with live animations

KALKI runs locally on your Windows PC and connects to cloud AI services
(Groq, Google Gemini, OpenAI, Anthropic) for intelligent responses.

Powered by Python, edge-tts, and modern web technologies.
```

- **Short description**: AI desktop assistant with voice control, Spotify, calendar, cybersecurity tools, and more.
- **Search terms**: AI assistant, voice control, desktop assistant, Spotify, productivity
- **Category**: Productivity
- **Subcategory**: Personal Productivity

### Screenshots
- Upload at least 1 screenshot (1366x768 recommended)
- Use the screenshots from your `screenshots/` folder or take new ones

### Privacy Policy
- URL: `https://github.com/Maher-Bhatt/KALKI/blob/main/TERMS.md`

### Age Rating
- Complete the IARC questionnaire
- KALKI has no violent/sexual/gambling content → likely rated "Everyone"

### Pricing
- Choose your pricing tier:
  - **Free** — no charge
  - **Free trial + paid** — users try before they buy
  - **Paid** — one-time purchase ($2.99 - $9.99 recommended for productivity tools)
  - **Subscription** — monthly/yearly recurring

---

## 4. Submit for Review

- Click **Submit to the Store**
- Microsoft will review your app (typically 1-3 business days)
- You'll receive an email when approved or if changes are needed

---

## 5. After Approval

Once approved, KALKI will appear in the Microsoft Store search results.
Users can find it by searching "Kalki" or "AI assistant".

### Updating the Store Version

When you release a new version:

1. Update the version number in `AppxManifest.xml` (e.g., `1.0.25.0`)
2. Run the bump script for all files
3. Rebuild: `powershell -ExecutionPolicy Bypass -File microsoft_store\build_msix.ps1`
4. Go to Partner Center → Kalki → **Update** → Upload new `.msix` → Submit

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Package validation failed" | Run `validate.ps1` and fix reported errors |
| "Publisher mismatch" | Ensure AppxManifest.xml Publisher matches Partner Center exactly |
| "Missing assets" | Run `generate_assets.py` to regenerate visual assets |
| "App crashes on launch" | Test locally with `sign.ps1` + sideload first |
| "Certification failed" | Check email for specific failure reasons |
