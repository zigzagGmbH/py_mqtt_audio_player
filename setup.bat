@echo off
setlocal enabledelayedexpansion

echo.
echo ===== MQTT Audio Player Setup =====
echo.

REM Check if uv exists
where uv >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Installing uv...
    powershell -Command "& {Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression}"
    call refreshenv >nul 2>nul
    
    where uv >nul 2>nul
    if !ERRORLEVEL! NEQ 0 (
        echo [ERROR] uv installation failed
        echo Please install manually: https://github.com/astral-sh/uv
        pause
        exit /b 1
    )
    echo [INFO] uv installed successfully!
)

REM Clean and install
echo [INFO] Installing dependencies...
if exist build rmdir /s /q build >nul 2>nul
if exist dist rmdir /s /q dist >nul 2>nul
if exist *.egg-info rmdir /s /q *.egg-info >nul 2>nul
if exist *.spec del *.spec >nul 2>nul
if exist audio-player.exe del audio-player.exe >nul 2>nul

uv sync
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Dependency installation failed
    pause
    exit /b 1
)

REM Menu
echo.
echo What would you like to do?
echo 1) Run the audio player (development mode)
echo 2) Build standalone executable
echo 3) Just setup (done)
echo.

set /p choice="Choose [1-3]: "

if "%choice%"=="1" goto run_dev
if "%choice%"=="2" goto build_only
goto show_usage

:run_dev
echo [INFO] Starting audio player...
echo.
uv run main.py
goto show_usage

:build_only
echo [INFO] Building executable...
uv add --group dev pyinstaller
uv run build.py
if %ERRORLEVEL% EQU 0 (
    echo [INFO] Build complete! Ready to run...
    echo.
    echo Your executable is ready: .\audio-player.exe
    echo Run it with: .\audio-player.exe
    echo.
    if exist build rmdir /s /q build >nul 2>nul
    if exist dist rmdir /s /q dist >nul 2>nul
    if exist *.egg-info rmdir /s /q *.egg-info >nul 2>nul
    if exist *.spec del *.spec >nul 2>nul
) else (
    echo [ERROR] Build failed
    pause
    exit /b 1
)
goto show_usage

:show_usage
echo.
echo ===== Usage Instructions =====
echo.
echo Development:  uv run main.py
echo Build binary: uv run build.py
echo Run binary:   .\audio-player.exe
echo.
echo Config: Edit config.yaml ^| Place .wav files in audio\
echo Done! 🎵
echo.
pause