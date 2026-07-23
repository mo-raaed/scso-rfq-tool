; Inno Setup Script for SCSO RFQ Tool
; =============================================
; This script creates a professional Windows installer that:
;   - Installs the application to Program Files
;   - Creates Desktop and Start Menu shortcuts
;   - Registers an uninstaller in Windows Settings
;
; Prerequisites:
;   1. Build the app with PyInstaller first:
;      cd scso_rfq_tool
;      pyinstaller build.spec
;   2. Install Inno Setup from https://jrsoftware.org/isinfo.php
;   3. Open this .iss file in Inno Setup Compiler and click Build
;
; The resulting Setup.exe can be distributed to employees.

[Setup]
AppName=SCSO RFQ Tool
AppVersion=1.0.0
AppPublisher=SCSO
AppPublisherURL=https://www.scsoco.com/
DefaultDirName={autopf}\SCSO RFQ Tool
DefaultGroupName=SCSO RFQ Tool
OutputDir=installer_output
OutputBaseFilename=SCSO_RFQ_Tool_Setup_v1.0.0
Compression=lzma2
SolidCompression=yes
; Uncomment when icon is ready:
; SetupIconFile=resources\icon.ico
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a Desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "startmenuicon"; Description: "Create a Start Menu shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
; Copy the entire PyInstaller output folder
Source: "dist\SCSO_RFQ_Tool\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Desktop shortcut
Name: "{commondesktop}\SCSO RFQ Tool"; Filename: "{app}\SCSO RFQ Tool.exe"; Tasks: desktopicon
; Start Menu shortcut
Name: "{group}\SCSO RFQ Tool"; Filename: "{app}\SCSO RFQ Tool.exe"; Tasks: startmenuicon
; Uninstall shortcut in Start Menu
Name: "{group}\Uninstall SCSO RFQ Tool"; Filename: "{uninstallexe}"

[Run]
; Option to launch the app after installation
Filename: "{app}\SCSO RFQ Tool.exe"; Description: "Launch SCSO RFQ Tool"; Flags: nowait postinstall skipifsilent
