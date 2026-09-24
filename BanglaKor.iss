; =========================================================
; Bangla Kor - Windows Installer (Inno Setup)
; =========================================================

#define MyAppName "Bangla Kor"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "Turzo"
#define MyAppURL "https://github.com/Turzo02/Bangla_Kor"
#define MyAppExeName "BanglaKor.exe"

[Setup]
AppId={{8C6C0C6D-1E8D-4E56-9A91-6A1F8A6C2026}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases

; Per-user install — no admin needed
DefaultDirName={localappdata}\Programs\Bangla Kor
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

OutputDir=installer
OutputBaseFilename=BanglaKor-Setup-v{#MyAppVersion}

Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

SetupIconFile=bangla-kor-icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
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

[Run]
Filename: "{app}\{#MyAppExeName}"; \
    Description: "Launch Bangla Kor"; \
    Flags: nowait postinstall skipifsilent