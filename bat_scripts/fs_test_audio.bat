@echo off
:: Auto HTTP Server Startup Script
:: This script waits for network connectivity and starts Python HTTP server

:: Configuration Variables
set "SERVER_PORT=8002"
set "SERVER_DIR=C:\Users\User\test_sounds"

echo Starting HTTP Server Auto-Boot Script...
echo Current time: %date% %time%

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

:: Start the HTTP server
echo Starting Python HTTP server on port %SERVER_PORT%...
echo Server will be accessible at: http://%ip%:%SERVER_PORT%
echo Serving directory: %SERVER_DIR%
echo.
echo Press Ctrl+C to stop the server
echo.
python -m http.server %SERVER_PORT% --bind %ip% --directory "%SERVER_DIR%"

:: If we get here, the server stopped
echo HTTP server has stopped.
@REM pause