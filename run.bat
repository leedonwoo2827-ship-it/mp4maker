@echo off
setlocal
chcp 65001 >nul

if not exist .venv (
    echo [ERROR] .venv\ not found. Run setup.bat first.
    exit /b 1
)

call .venv\Scripts\activate.bat

REM Verify ffmpeg before launching the UI so the user knows immediately.
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo [WARN] ffmpeg not on PATH. Rendering will fail until installed.
    echo        winget install Gyan.FFmpeg   then open a NEW PowerShell window.
    echo.
)

echo Launching mp4maker web UI...
echo A browser tab should open at http://localhost:8501
python -m streamlit run app.py
endlocal
