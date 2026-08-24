#define MyAppName "KALKI"
#define MyAppVersion "1.3.0"
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
OutputBaseFilename=KALKI_Setup_v1.3.0
LicenseFile=..\..\LICENSE
InfoBeforeFile=..\..\TERMS.md
SetupIconFile=..\..\assets\kalki_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=force
CloseApplicationsFilter=KALKI.exe,KALKI_Server.exe,KALKI_Listener.exe,KALKI_Setup_Wizard.exe,KALKI_Setup_Google.exe,KALKI_Setup_Spotify.exe
RestartApplications=no

[Code]
procedure StopKalkiProcesses;
var
  ResultCode: Integer;
begin
  { Inno's close-app filter handles normal windows. These explicit taskkill
    calls cover tray-hidden and helper processes that still hold DLL/EXE files. }
  Exec(ExpandConstant('{cmd}'), '/C taskkill /F /T /IM KALKI.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{cmd}'), '/C taskkill /F /T /IM KALKI_Server.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{cmd}'), '/C taskkill /F /T /IM KALKI_Listener.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{cmd}'), '/C taskkill /F /T /IM KALKI_Setup_Wizard.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{cmd}'), '/C taskkill /F /T /IM KALKI_Setup_Google.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec(ExpandConstant('{cmd}'), '/C taskkill /F /T /IM KALKI_Setup_Spotify.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(1200);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  StopKalkiProcesses;
  Result := '';
end;

[Types]
Name: "full"; Description: "Full installation"
Name: "compact"; Description: "Compact installation"
Name: "custom"; Description: "Custom installation"; Flags: iscustom

[Components]
Name: "core"; Description: "KALKI Core (required)"; Types: full compact custom; Flags: fixed
Name: "deepscan"; Description: "Deep website scanner (Playwright + Chromium, ~300 MB)"; Types: full

[Files]
; Keep every PyInstaller one-dir runtime isolated. Merging their _internal
; folders corrupts the dependencies required by each executable.
Source: "..\dist\KALKI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\dist\KALKI_Setup_Wizard\*"; DestDir: "{app}\services\setup_wizard"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\dist\KALKI_Server\*"; DestDir: "{app}\services\server"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\dist\KALKI_Listener\*"; DestDir: "{app}\services\listener"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\dist\KALKI_Setup_Google\*"; DestDir: "{app}\services\setup_google"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\dist\KALKI_Setup_Spotify\*"; DestDir: "{app}\services\setup_spotify"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\..\browsers\*"; DestDir: "{app}\browsers"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist; Components: deepscan

; Assets and structure
Source: "..\..\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\index.html"; DestDir: "{app}"; Flags: ignoreversion; Components: core
Source: "..\manifest.json"; DestDir: "{app}"; Flags: ignoreversion; Components: core
Source: "..\service-worker.js"; DestDir: "{app}"; Flags: ignoreversion; Components: core
Source: "..\config.example.py"; DestDir: "{app}"; Flags: ignoreversion; Components: core
Source: "..\plugins\*"; DestDir: "{app}\plugins"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion; Components: core
Source: "..\..\TERMS.md"; DestDir: "{app}"; Flags: ignoreversion; Components: core

[Dirs]
Name: "{app}\data"; Components: core

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

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


