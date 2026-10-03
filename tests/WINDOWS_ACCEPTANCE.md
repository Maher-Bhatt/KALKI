# Windows Acceptance Tests

| Feature | How to check | Expected | Windows 10 Result | Windows 11 Result |
|---|---|---|---|---|
| First run | Launch, finish the setup wizard | App opens, config saved under `%APPDATA%\KALKI` | PENDING | PENDING |
| Microphone and wake word | Say "hey kalki" | Presence changes to listening, mic chip shows live | PENDING | PENDING |
| Voice reply | Ask a question by voice | Reply is spoken; talking over it stops it | PENDING | PENDING |
| Chat with Groq key | Add key, send a message | Streamed reply, no key shown anywhere | PENDING | PENDING |
| Chat with no key | Remove key, send a message | Plain error with a fix, no crash | PENDING | PENDING |
| Screen vision | Ask about your screen | Asks permission, then answers | PENDING | PENDING |
| Documents | Drop a PDF, DOCX, XLSX | Extracted text shown before sending | PENDING | PENDING |
| Calendar | Connect Google | Today and upcoming events appear | PENDING | PENDING |
| Mail | Connect | Unread important count correct | PENDING | PENDING |
| Spotify | Connect | Play, pause, skip work | PENDING | PENDING |
| Reminders | Add one due in 2 minutes | Native Windows toast fires | PENDING | PENDING |
| Vault | Save, get, delete an entry | Round trip works, entries survive a restart | PENDING | PENDING |
| Backup | Create, then restore | Data identical after restore | PENDING | PENDING |
| Upgrade | Install over the previous version | Settings and memory kept | PENDING | PENDING |
| Uninstall | Remove | No helper processes left running | PENDING | PENDING |
