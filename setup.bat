@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo === mp4maker setup (Windows) ===
echo.

REM ---- 1. Python check --------------------------------------------------
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found on PATH.
    echo Install Python 3.11+ from https://www.python.org/downloads/ and re-run.
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [ok] Python !PYVER!

REM ---- 2. Virtual env ---------------------------------------------------
if not exist .venv (
    echo [..] Creating virtual environment in .venv\
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] venv creation failed.
        exit /b 1
    )
) else (
    echo [ok] .venv\ already exists
)

call .venv\Scripts\activate.bat

REM ---- 3. Dependencies --------------------------------------------------
echo [..] Upgrading pip
python -m pip install --upgrade pip --quiet --disable-pip-version-check

echo [..] Installing requirements
pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo [ERROR] pip install failed. See output above.
    exit /b 1
)
echo [ok] Python packages installed

REM ---- 4. ffmpeg check --------------------------------------------------
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo.
    echo [WARN] ffmpeg not found on PATH.
    echo        Install with:  winget install Gyan.FFmpeg
    echo        Then open a NEW PowerShell window and re-run setup.bat to verify.
) else (
    for /f "tokens=3" %%v in ('ffmpeg -version ^| findstr /b "ffmpeg version"') do set FFVER=%%v
    echo [ok] ffmpeg !FFVER!
)

REM ---- 5. _assets check -------------------------------------------------
if not exist _assets (
    echo.
    echo [info] _assets\ not found. Creating empty folder.
    echo        Put your chNN_bundle directories inside _assets\ before running.
    mkdir _assets
) else (
    echo [ok] _assets\ exists
)

echo.
echo === setup complete ===
echo Next:  run.bat     ^(launches the web UI in your browser^)
echo or:    .venv\Scripts\activate ^&^& python -m mp4maker --probe
endlocal
