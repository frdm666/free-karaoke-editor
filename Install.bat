@echo off
rem Razovaya nastroyka: proveryaet ffmpeg i stavit nuzhnye biblioteki.
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"

rem The setup writes down the Python it installed into: whatever put the
rem libraries on the disk is what opens the program. Without it a machine with
rem several Pythons could install into one and start on another.
set "PY="
if exist "app\.python-path" set /p PY=<"app\.python-path"
if not defined PY goto findpy
"%PY%" -c "" >nul 2>&1
if not errorlevel 1 goto havepy
set "PY="
:findpy
where py >nul 2>&1
if %errorlevel%==0 (set "PY=py") else (set "PY=python")
:havepy

"%PY%" --version >nul 2>&1
if errorlevel 1 goto nopython

"%PY%" "app\tools\setup_check.py"
echo.
pause
exit /b

:nopython
echo.
echo   Python ne nayden.
echo.
echo   Skachayte ego s https://python.org
echo   Pri ustanovke obyazatelno otmette galochku
echo   "Add Python to PATH", inache nichego ne zarabotaet.
echo.
pause
