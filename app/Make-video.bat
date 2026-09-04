@echo off
rem Peretaschite na etot znachok gotovuyu stranicu karaoke (.html).
rem Bez peretaskivaniya - pokazhet spisok stranic ryadom i dast vybrat.
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"

rem The setup writes down the Python it installed into: whatever put the
rem libraries on the disk is what opens the program. Without it a machine with
rem several Pythons could install into one and start on another.
set "PY="
if exist "%~dp0.python-path" set /p PY=<"%~dp0.python-path"
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

"%PY%" "%~dp0tools\video.py" %*
echo.
pause
exit /b

:nopython
echo.
echo   Python ne nayden. Zapustite snachala "..\Install.bat".
echo.
pause
