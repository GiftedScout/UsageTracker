@echo off
chcp 65001 >nul
REM UsageTracker v0.2.0 Build Script
REM Stage 1: PyInstaller → dist/UsageTracker/ 
REM Stage 2: Inno Setup → installer_output/UsageTracker_Setup.exe

echo ========================================
echo  UsageTracker v0.2.0 Build
echo ========================================

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

REM Stage 1: PyInstaller
echo.
echo [1/2] PyInstaller: Building exe...
python -m PyInstaller UsageTracker.spec
if %errorlevel% neq 0 (
    echo [ERROR] PyInstaller failed
    pause
    exit /b 1
)
echo [OK] PyInstaller build complete

REM Stage 2: Inno Setup
echo.
echo [2/2] Inno Setup: Building installer...
if exist "%ProgramFiles%\Inno Setup 7\ISCC.exe" (
    "%ProgramFiles%\Inno Setup 7\ISCC.exe" installer.iss
) else if exist "C:\Program Files\Inno Setup 7\ISCC.exe" (
    "C:\Program Files\Inno Setup 7\ISCC.exe" installer.iss
) else if exist "%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe" (
    "%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe" installer.iss
) else if exist "C:\Program Files (x86)\Inno Setup 7\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 7\ISCC.exe" installer.iss
) else (
    echo [WARNING] Inno Setup ISCC.exe not found at common paths.
    echo          Installer not built. Install Inno Setup 7 first.
    pause
    exit /b 1
)

if %errorlevel% neq 0 (
    echo [ERROR] Inno Setup failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Build complete!
echo  Installer: installer_output\UsageTracker_Setup_v0.2.0.exe
echo ========================================
pause
