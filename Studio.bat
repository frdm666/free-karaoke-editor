@echo off
rem Karaoke Studio - okno programmy. Zakroyte eto okno, chtoby zakonchit.
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

"%PY%" "app\studio.py"
echo.
echo   Studiya zakryta.
pause
exit /b

:nopython
echo.
echo   Python ne nayden. Zapustite snachala "Install.bat".
echo.
pause
