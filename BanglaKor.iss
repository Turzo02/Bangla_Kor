; =========================================================
; Bangla Kor - Windows Installer
; =========================================================

#define MyAppName "Bangla Kor"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Bangla Kor"
#define MyAppExeName "BanglaKor.exe"

[Setup]
AppId={{8C6C0C6D-1E8D-4E56-9A91-6A1F8A6C2026}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={autopf}\Bangla Kor
DefaultGroupName={#MyAppName}

OutputDir=installer
OutputBaseFilename=BanglaKor-Setup

Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

SetupIconFile=bangla-kor-icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startup"; \
    Description: "Start Bangla Kor with Windows"; \
    GroupDescription: "Startup options:"; \
    Flags: checkedonce

Name: "desktopicon"; \
    Description: "Create a desktop shortcut"; \
    GroupDescription: "Additional shortcuts:"; \
    Flags: unchecked

[Files]
Source: "dist\BanglaKor\*"; \
    DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Bangla Kor"; \
    Filename: "{app}\{#MyAppExeName}"; \
    WorkingDir: "{app}"; \
    IconFilename: "{app}\{#MyAppExeName}"

Name: "{autodesktop}\Bangla Kor"; \
    Filename: "{app}\{#MyAppExeName}"; \
    WorkingDir: "{app}"; \
    Tasks: desktopicon; \
    IconFilename: "{app}\{#MyAppExeName}"

[Registry]
Root: HKCU; \
    Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; \
    ValueName: "BanglaKor"; \
    ValueData: """{app}\{#MyAppExeName}"" --startup"; \
    Flags: uninsdeletevalue; \
    Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; \
    Description: "Launch Bangla Kor"; \
    Flags: nowait postinstall skipifsilent
