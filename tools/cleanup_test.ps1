# UsageTracker GUI 测试清理脚本
# 用途：测试完 GUI 版后运行，清除所有 GUI 留下的痕迹，不影响 CLI 版

$ErrorActionPreference = 'SilentlyContinue'

Write-Host "=== UsageTracker GUI 测试清理 ===" -ForegroundColor Cyan

# 1. 停掉 GUI 进程
$proc = Get-Process UsageTracker -ErrorAction SilentlyContinue
if ($proc) {
    $proc | Stop-Process -Force
    Write-Host "[OK] 已停止 UsageTracker 进程 (PID $($proc.Id))" -ForegroundColor Green
} else {
    Write-Host "[--] UsageTracker 进程未运行" -ForegroundColor DarkGray
}

Start-Sleep -Milliseconds 500

# 2. 删除启动文件夹中的 GUI 快捷方式
$lnk = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\UsageTracker.lnk"
if (Test-Path $lnk) {
    # 读取快捷方式目标，只删 GUI 版（dist 目录下的）
    $shell = New-Object -ComObject WScript.Shell
    $sc = $shell.CreateShortcut($lnk)
    $target = $sc.TargetPath
    if ($target -like "*WorkBuddy*20260416101234*" -or $target -like "*dist\UsageTracker*") {
        Remove-Item $lnk -Force
        Write-Host "[OK] 已删除 GUI 开机自启快捷方式 (目标: $target)" -ForegroundColor Green
    } else {
        Write-Host "[SKIP] 快捷方式目标是 CLI 版，保留: $target" -ForegroundColor Yellow
    }
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($shell) | Out-Null
} else {
    Write-Host "[--] 启动文件夹无 UsageTracker 快捷方式" -ForegroundColor DarkGray
}

# 3. 确认注册表 CLI 自启条目完好
$reg = (Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run").UsageTracker
if ($reg -like "*20260330195834*") {
    Write-Host "[OK] CLI 注册表自启完好: $reg" -ForegroundColor Green
} elseif ($reg) {
    Write-Host "[WARN] 注册表自启条目指向未知路径: $reg" -ForegroundColor Yellow
} else {
    Write-Host "[--] 注册表无 UsageTracker 自启条目（CLI 版未启用自启）" -ForegroundColor DarkGray
}

# 4. 显示当前状态摘要
Write-Host ""
Write-Host "=== 清理完成，当前状态 ===" -ForegroundColor Cyan
Write-Host "CLI 进程: $(if (Get-Process -Name pythonw -ErrorAction SilentlyContinue | Where-Object {$_.Path -like '*pythonw*'}) {'运行中'} else {'未运行'})"
Write-Host "GUI 进程: $(if (Get-Process UsageTracker -ErrorAction SilentlyContinue) {'还在运行！请手动检查'} else {'已停止'})"
Write-Host "GUI 自启快捷方式: $(if (Test-Path $lnk) {'存在（请检查）'} else {'不存在 ✓'})"
