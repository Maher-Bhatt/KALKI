#define MyAppName "KALKI"
#define MyAppVersion "1.0.20"
#define MyAppPublisher "KALKI Technologies"
#define MyAppExeName "KALKI.exe"

[Setup]
AppId={{9F5F5F0D-B4A4-4A8E-87AE-4DFB8C8A3E7D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\KALKI
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
OutputDir=..\..\Output
OutputBaseFilename=KALKI_Setup
LicenseFile=..\..\LICENSE
SetupIconFile=..\..\assets\kalki_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=force
CloseApplicationsFilter=*.exe
RestartApplications=yes


[Components]
Name: "core"; Description: "KALKI Core (required)"; Types: full compact custom; Flags: fixed
Name: "deepscan"; Description: "Deep website scanner (Playwright + Chromium, ~300 MB)"; Types: full

[Files]
; The 4 EXEs
Source: "..\dist\KALKI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\dist\KALKI_Setup_Wizard\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\dist\KALKI_Server\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\dist\KALKI_Listener\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\dist\KALKI_Setup_Google\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\dist\KALKI_Setup_Spotify\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\..\browsers\*"; DestDir: "{app}\browsers"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core

; Assets and structure
Source: "..\..\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\index.html"; DestDir: "{app}"; Flags: ignoreversion; Components: core
Source: "..\config.example.py"; DestDir: "{app}"; Flags: ignoreversion; Components: core
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion; Components: core

[Dirs]
Name: "{app}\data"; Components: core

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "KALKI"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue

[Run]
; Run KALKI itself post-install
Filename: "{app}\KALKI.exe"; Description: "Launch KALKI"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM KALKI.exe /T"; Flags: runhidden
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM KALKI_Server.exe /T"; Flags: runhidden
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM KALKI_Listener.exe /T"; Flags: runhidden
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM KALKI_Setup_Wizard.exe /T"; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\browsers"
Type: filesandordirs; Name: "{app}"


