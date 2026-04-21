; UsageTracker Inno Setup 安装脚本
; 版本: 0.1.0

#define MyAppName "UsageTracker"
#define MyAppVersion "0.1.0"
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
; 显示语言选择对话框
ShowLanguageDialog=yes
; 允许升级安装（不要求先卸载）
; DisableReadyPage=no 默认显示准备页面
; 升级时覆盖旧文件但不删除用户数据
UsePreviousAppDir=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"

[CustomMessages]
english.DesktopIcon=Create desktop shortcut
english.StartupIcon=Auto-start on boot
english.RunNow=Run {#MyAppName} now
english.WriteLangFailed=Failed to write language config
english.KillProcessFailed=Failed to stop running UsageTracker. Please close it manually and retry.
english.OldVersionDetected=An older version was detected in a different location.
english.MigratingData=Migrating data from old location...
english.MigrationFailed=Data migration failed. Your old data is preserved at:
english.DowngradeWarning=You are installing an older version than what is currently installed.%n%nIt is recommended to cancel and download the latest version.
english.DowngradeTitle=Downgrade Detected
english.UpgradeRestart=UsageTracker needs to restart to complete the upgrade.
english.UpgradingFrom=Upgrading from version {0}
chinesesimplified.DesktopIcon=创建桌面快捷方式
chinesesimplified.StartupIcon=开机自动启动
chinesesimplified.RunNow=立即运行 {#MyAppName}
chinesesimplified.WriteLangFailed=写入语言配置失败
chinesesimplified.KillProcessFailed=无法停止正在运行的 UsageTracker，请手动关闭后重试。
chinesesimplified.OldVersionDetected=检测到旧版本安装在不同位置。
chinesesimplified.MigratingData=正在从旧位置迁移数据...
chinesesimplified.MigrationFailed=数据迁移失败，旧数据保留在：
chinesesimplified.DowngradeWarning=你正在安装的版本低于当前已安装的版本。%n%n建议取消安装并下载最新版本。
chinesesimplified.DowngradeTitle=检测到降级安装
chinesesimplified.UpgradeRestart=UsageTracker 需要重启以完成升级。
chinesesimplified.UpgradingFrom=正在从版本 {0} 升级

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; Flags: unchecked
Name: "startupicon"; Description: "{cm:StartupIcon}"; Flags: checkedonce

[Files]
; 程序文件：忽略版本号（允许覆盖升级）
Source: "dist\UsageTracker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "config\*,data\*,reports\*,logs\*,bridge\*,feedback\*"
; 确保子目录结构存在（空目录也需要）
Source: "dist\UsageTracker\config\.gitkeep"; DestDir: "{app}\config"; Flags: ignoreversion onlyifdoesntexist
Source: "dist\UsageTracker\data\.gitkeep"; DestDir: "{app}\data"; Flags: ignoreversion onlyifdoesntexist
Source: "dist\UsageTracker\reports\.gitkeep"; DestDir: "{app}\reports"; Flags: ignoreversion onlyifdoesntexist

[Icons]
; 开始菜单快捷方式
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
; 桌面快捷方式
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
; 启动文件夹快捷方式
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: startupicon; IconFilename: "{app}\{#MyAppExeName}"

[Run]
; 安装完成后可选运行
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:RunNow}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; 卸载时删除启动文件夹快捷方式
Filename: "{cmd}"; Parameters: "/C del ""{userstartup}\{#MyAppName}.lnk"""; Flags: runhidden

[UninstallDelete]
; 清理运行时生成的缓存目录
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\bridge"
Type: filesandordirs; Name: "{app}\feedback"
; 旧版数据目录（v0.1.0-beta 可能存在）
Type: filesandordirs; Name: "{%LOCALAPPDATA}\UsageTracker"
; 清理空的子目录
Type: dirifempty; Name: "{app}\config"
Type: dirifempty; Name: "{app}\data"
Type: dirifempty; Name: "{app}\reports"

[InstallDelete]
; 升级时清理旧版可能遗留的废弃文件
Type: files; Name: "{app}\*.pyc"
Type: files; Name: "{app}\*.pyo"

[Code]
// ==========================================
// 辅助函数：获取已安装版本号
// ==========================================
function GetInstalledVersion(): String;
var
  ConfigPath: string;
  AnsiContent: AnsiString;
  ConfigContent: string;
  VersionPos: Integer;
  StartPos: Integer;
  EndPos: Integer;
begin
  Result := '';
  ConfigPath := ExpandConstant('{app}\config\config.json');
  if LoadStringFromFile(ConfigPath, AnsiContent) then
  begin
    ConfigContent := string(AnsiContent);
    VersionPos := Pos('"version"', ConfigContent);
    if VersionPos > 0 then
    begin
      // 找到 "version": "x.x.x" 中的版本号
      StartPos := Pos('"', Copy(ConfigContent, VersionPos + 10, Length(ConfigContent)));
      if StartPos > 0 then
      begin
        StartPos := VersionPos + 9 + StartPos;
        EndPos := Pos('"', Copy(ConfigContent, StartPos + 1, Length(ConfigContent)));
        if EndPos > 0 then
          Result := Copy(ConfigContent, StartPos + 1, EndPos - 1);
      end;
    end;
  end;
end;

// ==========================================
// 辅助函数：比较两个版本号字符串
// 返回值: >0 表示 v1 > v2, 0 表示相等, <0 表示 v1 < v2
// ==========================================
function CompareVersions(v1, v2: string): Integer;
var
  p1, p2: Integer;
  n1, n2: Integer;
begin
  Result := 0;
  while (Result = 0) and ((v1 <> '') or (v2 <> '')) do
  begin
    // 提取 v1 下一段数字
    p1 := Pos('.', v1);
    if p1 > 0 then
    begin
      n1 := StrToIntDef(Copy(v1, 1, p1 - 1), 0);
      v1 := Copy(v1, p1 + 1, Length(v1));
    end
    else if v1 <> '' then
    begin
      // 处理 "0.1.0-beta" 这种带后缀的情况
      p1 := Pos('-', v1);
      if p1 > 0 then
      begin
        n1 := StrToIntDef(Copy(v1, 1, p1 - 1), 0);
        v1 := '';
      end
      else
      begin
        n1 := StrToIntDef(v1, 0);
        v1 := '';
      end;
    end
    else
      n1 := 0;

    // 提取 v2 下一段数字
    p2 := Pos('.', v2);
    if p2 > 0 then
    begin
      n2 := StrToIntDef(Copy(v2, 1, p2 - 1), 0);
      v2 := Copy(v2, p2 + 1, Length(v2));
    end
    else if v2 <> '' then
    begin
      p2 := Pos('-', v2);
      if p2 > 0 then
      begin
        n2 := StrToIntDef(Copy(v2, 1, p2 - 1), 0);
        v2 := '';
      end
      else
      begin
        n2 := StrToIntDef(v2, 0);
        v2 := '';
      end;
    end
    else
      n2 := 0;

    if n1 < n2 then Result := -1
    else if n1 > n2 then Result := 1;
  end;
end;

// ==========================================
// 辅助函数：停止正在运行的 UsageTracker 进程
// ==========================================
function KillUsageTracker(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  // 尝试通过 taskkill 优雅终止
  Exec('taskkill.exe', '/F /IM UsageTracker.exe /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  // taskkill 返回 0 表示成功，128 表示没有找到进程，都算 OK
  if (ResultCode <> 0) and (ResultCode <> 128) then
  begin
    Result := False;
  end;
end;

// ==========================================
// 辅助函数：从旧版目录迁移数据
// 处理 v0.1.0-beta 的旧数据位置
// ==========================================
procedure MigrateFromOldLocation();
var
  OldDataDir: string;
  NewDataDir: string;
  OldConfigDir: string;
  NewConfigDir: string;
  ResultCode: Integer;
begin
  OldDataDir := ExpandConstant('{%LOCALAPPDATA}\UsageTracker');
  NewDataDir := ExpandConstant('{app}\data');
  OldConfigDir := ExpandConstant('{%LOCALAPPDATA}\UsageTracker\config');
  NewConfigDir := ExpandConstant('{app}\config');

  // 检查旧目录是否存在
  if not DirExists(OldDataDir) then
    Exit;

  // 迁移数据库
  if FileExists(OldDataDir + '\usage_data.db') and not FileExists(NewDataDir + '\usage_data.db') then
  begin
    ForceDirectories(NewDataDir);
    Exec('xcopy.exe', '"' + OldDataDir + '\usage_data.db" "' + NewDataDir + '\" /Y', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;

  // 迁移配置
  if FileExists(OldConfigDir + '\config.json') and not FileExists(NewConfigDir + '\config.json') then
  begin
    ForceDirectories(NewConfigDir);
    Exec('xcopy.exe', '"' + OldConfigDir + '\config.json" "' + NewConfigDir + '\" /Y', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;

  // 迁移报告目录
  if DirExists(OldDataDir + '\reports') and not DirExists(ExpandConstant('{app}\reports')) then
  begin
    Exec('xcopy.exe', '"' + OldDataDir + '\reports" "' + ExpandConstant('{app}\reports') + '\" /E /I /Y', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

// ==========================================
// 安装前检查：降级警告 + 停止旧进程 + 数据迁移
// ==========================================
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  InstalledVer: string;
  NewVer: string;
  MsgBoxResult: Integer;
begin
  Result := '';
  NeedsRestart := False;
  NewVer := '{#MyAppVersion}';

  // 1. 检查是否有已安装版本
  InstalledVer := GetInstalledVersion();
  if InstalledVer <> '' then
  begin
    // 2. 降级检测
    if CompareVersions(NewVer, InstalledVer) < 0 then
    begin
      MsgBoxResult := MsgBox(
        CustomMessage('DowngradeWarning'),
        mbError, MB_OKCANCEL);
      if MsgBoxResult <> IDOK then
      begin
        Result := CustomMessage('DowngradeTitle');
        Exit;
      end;
    end;
  end;

  // 3. 停止正在运行的进程
  if not KillUsageTracker() then
  begin
    Result := CustomMessage('KillProcessFailed');
    Exit;
  end;

  // 4. 从旧位置迁移数据（v0.1.0-beta → v0.1.0）
  MigrateFromOldLocation();
end;

// ==========================================
// 安装后处理：写入语言配置 + 版本号更新
// ==========================================
procedure CurStepChanged(CurStep: TSetupStep);
var
  LangCode: string;
  ConfigPath: string;
  AnsiContent: AnsiString;
  ConfigContent: string;
begin
  if CurStep = ssPostInstall then
  begin
    // 根据安装界面选择的语言确定语言代码
    if ActiveLanguage = 'chinesesimplified' then
      LangCode := 'zh-CN'
    else
      LangCode := 'en';

    ConfigPath := ExpandConstant('{app}\config\config.json');

    // 如果配置文件已存在（升级安装），读取并修改 language 和 version 字段
    if LoadStringFromFile(ConfigPath, AnsiContent) then
    begin
      ConfigContent := string(AnsiContent);
      // 更新 language 字段
      if Pos('"language"', ConfigContent) > 0 then
      begin
        StringChangeEx(ConfigContent, '"language": "zh-CN"', '"language": "' + LangCode + '"', True);
        StringChangeEx(ConfigContent, '"language": "en"', '"language": "' + LangCode + '"', True);
      end
      else
      begin
        // 旧配置没有 language 字段，在 auto_start 前插入
        if Pos('"auto_start"', ConfigContent) > 0 then
          StringChangeEx(ConfigContent, '"auto_start"', '"language": "' + LangCode + '",' + #13#10 + '  "auto_start"', True);
      end;

      // 更新 version 字段
      StringChangeEx(ConfigContent, '"version": "0.1.0-beta"', '"version": "{#MyAppVersion}"', True);
      // 也处理其他可能的历史版本号格式
      StringChangeEx(ConfigContent, '"version": "0.1.0"', '"version": "{#MyAppVersion}"', True);

      SaveStringToFile(ConfigPath, AnsiString(ConfigContent), False);
    end
    else
    begin
      // 首次安装：创建默认配置文件
      ForceDirectories(ExpandConstant('{app}\config'));
      ConfigContent := '{' + #13#10 +
        '  "version": "' + '{#MyAppVersion}' + '",' + #13#10 +
        '  "language": "' + LangCode + '",' + #13#10 +
        '  "theme": "fairy_tale",' + #13#10 +
        '  "data_retention": "unlimited",' + #13#10 +
        '  "check_interval": 5,' + #13#10 +
        '  "auto_start": true,' + #13#10 +
        '  "auto_show_daily_report": true,' + #13#10 +
        '  "privacy_accepted": false,' + #13#10 +
        '  "browsers": [],' + #13#10 +
        '  "game_dirs": [],' + #13#10 +
        '  "ignored_apps": [],' + #13#10 +
        '  "custom_categories": []' + #13#10 +
        '}';
      SaveStringToFile(ConfigPath, AnsiString(ConfigContent), False);
    end;
  end;
end;

// ==========================================
// 卸载前确认：提醒用户数据保留选项
// ==========================================
function InitializeUninstall(): Boolean;
var
  DataDir: string;
  ConfigDir: string;
  MsgBoxResult: Integer;
begin
  Result := True;
  DataDir := ExpandConstant('{app}\data');
  ConfigDir := ExpandConstant('{app}\config');

  // 如果存在用户数据，提示用户
  if DirExists(DataDir) or DirExists(ConfigDir) then
  begin
    // Inno Setup 的默认卸载界面已经包含了"是否保留个人数据"的提示（通过 UninstallDelete 控制）
    // 这里不做额外弹窗，保持简洁
  end;
end;
