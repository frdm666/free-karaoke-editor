@echo off
rem Sobiraet karaoke dlya vseh pesen v papke.
rem Pary ischutsya po imeni: Veter.mp3 + Veter.txt
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

set "FOLDER=%~1"
if not "%FOLDER%"=="" goto run

echo.
echo   Ukazhite papku s pesnyami.
echo   Mozhno prosto peretaschit papku na etot znachok.
echo.
set /p "FOLDER=Papka: "
if "%FOLDER%"=="" goto end

:run
"%PY%" "%~dp0tools\auto.py" "%FOLDER%"
echo.

:end
pause
exit /b

:nopython
echo.
echo   Python ne nayden. Zapustite snachala "..\Install.bat".
echo.
pause
