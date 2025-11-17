@echo off
setlocal enabledelayedexpansion

:: Wait for network to be ready
echo Waiting for network connectivity...
:check_network
ping -n 1 8.8.8.8 >nul 2>&1
if errorlevel 1 (
    echo Network not ready, waiting 5 seconds...
    timeout /t 5 /nobreak >nul
    goto check_network
)

echo Network is ready!

:: Get IPv4 address of Ethernet adapter
echo Checking Ethernet adapter IP address...
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr "IPv4 Address" ^| findstr "192.168"') do (
    for /f "tokens=* delims= " %%j in ("%%i") do (
        set "ip=%%j"
        goto got_ip
    )
)

:got_ip
:: Clean up the IP address (remove leading spaces)
for /f "tokens=* delims= " %%a in ("%ip%") do set ip=%%a

if defined ip (
    echo Ethernet IPv4 Address: %ip%
) else (
    echo Warning: Could not detect Ethernet IPv4 address
    echo Using all interfaces binding instead...
    set "ip=0.0.0.0"
)

:: Set paths
set "UV_PATH=C:\Users\User\.local\bin\uv.exe"
set "WORK_DIR=C:\Users\User\ve_ai-cockpit-testarea\01_audio_player"

:: Change to working directory
echo Changing to working directory: %WORK_DIR%
cd /d "%WORK_DIR%"

if not exist "%WORK_DIR%" (
    echo ERROR: Working directory does not exist: %WORK_DIR%
    exit /b 1
)

if not exist "%UV_PATH%" (
    echo ERROR: UV executable not found: %UV_PATH%
    exit /b 1
)

echo Starting shaker player...

:: Start all shaker player
start /b "" "%UV_PATH%" run main.py -c config-shakers.yaml 


echo shaker player started!