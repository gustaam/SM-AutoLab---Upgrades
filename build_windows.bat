@echo off
setlocal EnableExtensions EnableDelayedExpansion

where py >nul 2>nul
if %errorlevel%==0 (set PYTHON=py) else (set PYTHON=python)

REM Read the application version from VERSION so the EXE name can never go stale.
set "APP_VERSION="
for /f "usebackq delims=" %%V in ("VERSION") do if not defined APP_VERSION set "APP_VERSION=%%V"
if not defined APP_VERSION goto :erro

echo Versao detectada: v!APP_VERSION!

%PYTHON% -m pip install -r requirements.txt
if errorlevel 1 goto :erro
%PYTHON% -m pip install --upgrade pyinstaller
if errorlevel 1 goto :erro
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "*.spec" del /q "*.spec"

%PYTHON% -m PyInstaller --noconfirm --clean --onefile --windowed --name "SM AutoLab v!APP_VERSION!" --collect-submodules selenium --collect-data selenium --collect-data customtkinter --icon "SM AutoLab.ico" --add-data "SM AutoLab.ico;." --add-data "assets;assets" --add-data "VERSION;." main.py
if errorlevel 1 goto :erro

%PYTHON% -m PyInstaller --noconfirm --clean --onefile --windowed --name "SM AutoLab Updater" updater.py
if errorlevel 1 goto :erro

if not exist "dist\SM AutoLab v!APP_VERSION!.exe" goto :erro
echo.
echo BUILD CONCLUIDO: dist\SM AutoLab v!APP_VERSION!.exe e dist\SM AutoLab Updater.exe
pause
exit /b 0

:erro
echo.
echo BUILD FALHOU
pause
exit /b 1
