; UsageTracker Inno Setup 安装脚本
; 版本: 0.1.0-beta

#define MyAppName "UsageTracker"
#define MyAppVersion "0.1.0-beta"
#define MyAppPublisher "chaos"
#define MyAppURL ""
#define MyAppExeName "UsageTracker.exe"
#define MyAppDir "localuserapp:UsageTracker"

[Setup]
AppId={{B8F1A2C3-D4E5-4F6A-B7C8-9D0E1F2A3B4C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={%LOCALAPPDATA}\Programs\UsageTracker
DefaultGroupName={#MyAppName}
OutputDir=installer_output
OutputBaseFilename=UsageTracker_Setup_{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; 不需要管理员权限
PrivilegesRequired=lowest
; 中文界面
ShowLanguageDialog=no

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; Flags: unchecked
Name: "startupicon"; Description: "开机自动启动"; Flags: checkedonce

[Files]
; 递归复制整个 dist 目录内容
Source: "dist\UsageTracker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; 开始菜单快捷方式
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
; 桌面快捷方式
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
; 启动文件夹快捷方式
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: startupicon; IconFilename: "{app}\{#MyAppExeName}"

[Run]
; 安装完成后可选运行
Filename: "{app}\{#MyAppExeName}"; Description: "立即运行 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; 卸载时删除启动文件夹快捷方式
Filename: "{cmd}"; Parameters: "/C del ""{userstartup}\{#MyAppName}.lnk"""; Flags: runhidden

[UninstallDelete]
; 清理数据子目录（日志、缓存等）
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\bridge"
Type: filesandordirs; Name: "{app}\feedback"
; 旧版数据目录
Type: filesandordirs; Name: "{%LOCALAPPDATA}\UsageTracker"
