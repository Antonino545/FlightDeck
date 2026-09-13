; Inno Setup Script for FlightDeck
; Builds a complete Windows installer (FlightDeck-Setup.exe)

#ifndef AppVersion
#define AppVersion "1.0.0"
#endif

[Setup]
AppId={{67A41E1C-A47E-4E65-A656-11884C0F700B}
AppName=FlightDeck
AppVersion={#AppVersion}
AppVerName=FlightDeck {#AppVersion}
AppPublisher=FlightDeck
AppPublisherURL=https://github.com/Antonino545/FlightDeck
AppSupportURL=https://github.com/Antonino545/FlightDeck/issues
AppUpdatesURL=https://github.com/Antonino545/FlightDeck/releases
DefaultDirName={autopf}\FlightDeck
DefaultGroupName=FlightDeck
AllowNoIcons=yes
LicenseFile=..\..\LICENSE
OutputDir=..\..\dist
OutputBaseFilename=FlightDeck-Setup
SetupIconFile=..\..\assets\icon.ico
UninstallDisplayIcon={app}\FlightDeck.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes
RestartApplications=no
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Launch FlightDeck automatically at Windows startup"; GroupDescription: "Startup options:"; Flags: unchecked

[Files]
Source: "..\..\dist\FlightDeck\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\FlightDeck"; Filename: "{app}\FlightDeck.exe"; IconFilename: "{app}\FlightDeck.exe"
Name: "{group}\{cm:UninstallProgram,FlightDeck}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\FlightDeck"; Filename: "{app}\FlightDeck.exe"; Tasks: desktopicon; IconFilename: "{app}\FlightDeck.exe"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "FlightDeck"; ValueData: """{app}\FlightDeck.exe"" --silent --autostart"; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\FlightDeck.exe"; Description: "{cm:LaunchProgram,FlightDeck}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\*.log"
