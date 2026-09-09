@echo off
setlocal EnableExtensions EnableDelayedExpansion

echo ==========================================
echo   SM AutoLab - Build Windows
echo ==========================================
echo.

set "APP_VERSION="
for /f "usebackq delims=" %%V in ("VERSION") do if not defined APP_VERSION set "APP_VERSION=%%V"

if not defined APP_VERSION (
    echo ERRO: nao foi possivel ler o arquivo VERSION.
    pause
    exit /b 1
)

echo Versao detectada: v!APP_VERSION!
echo.

REM ----------------------------------------------------------
REM VALIDACAO DE CONSISTENCIA DO CODIGO-FONTE
REM Impede build com interface/patch de versoes conflitantes.
REM ----------------------------------------------------------
echo Verificando codigo-fonte da versao v!APP_VERSION!...
%SystemRoot%\System32\findstr.exe /c:"def _renderizar_calendario_arquivos" interface.py >nul
if errorlevel 1 (
    echo ERRO: interface.py nao contem o calendario de Arquivos.
    goto :erro
)
%SystemRoot%\System32\findstr.exe /c:"Canvas(" interface.py >nul
if errorlevel 1 (
    echo ERRO: interface.py nao contem o calendario nativo Canvas.
    goto :erro
)
%SystemRoot%\System32\findstr.exe /c:"ARQUIVOS_DIAS = 60" interface.py >nul
if errorlevel 1 (
    echo ERRO: interface.py nao esta configurado para 60 dias.
    goto :erro
)
%SystemRoot%\System32\findstr.exe /c:"tkcalendar" interface.py >nul
if not errorlevel 1 (
    echo ERRO: interface.py ainda contem dependencia externa tkcalendar.
    goto :erro
)
%SystemRoot%\System32\findstr.exe /c:"app_class.abrir_historico_planilha = _abrir_historico_planilha_v266" patch_v266.py >nul
if not errorlevel 1 (
    echo ERRO: patch_v266.py esta sobrescrevendo a tela Arquivos.
    goto :erro
)
echo Validacao do codigo-fonte: OK
echo.

REM Remover caches Python locais para evitar referencias obsoletas.
for /d /r %%D in (__pycache__) do if exist "%%D" rmdir /s /q "%%D" >nul 2>nul

set "PYTHON="
where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON=py"
    goto :python_ok
)

where python >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON=python"
    goto :python_ok
)

echo ERRO: Python nao foi encontrado.
pause
exit /b 1

:python_ok
%PYTHON% --version
if errorlevel 1 goto :erro

%PYTHON% -m pip install --upgrade pip
if errorlevel 1 goto :erro
%PYTHON% -m pip install -r requirements.txt
if errorlevel 1 goto :erro
%PYTHON% -m pip install --upgrade pyinstaller
if errorlevel 1 goto :erro

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "*.spec" del /q "*.spec"

echo.
echo Gerando SM AutoLab v!APP_VERSION!...
%PYTHON% -m PyInstaller --noconfirm --clean --onefile --windowed --name "SM AutoLab" --collect-submodules selenium --collect-data selenium --collect-data customtkinter --icon "SM AutoLab.ico" --add-data "SM AutoLab.ico;." --add-data "assets;assets" --add-data "VERSION;." main.py
if errorlevel 1 goto :erro

if not exist "dist\SM AutoLab.exe" (
    echo ERRO: executavel principal nao foi gerado.
    goto :erro
)

echo.
echo Gerando SM AutoLab Updater...
%PYTHON% -m PyInstaller --noconfirm --clean --onefile --windowed --name "SM AutoLab Updater" updater.py
if errorlevel 1 goto :erro

if not exist "dist\SM AutoLab Updater.exe" (
    echo ERRO: updater nao foi gerado.
    goto :erro
)

echo.
echo BUILD CONCLUIDO:
echo dist\SM AutoLab.exe
echo dist\SM AutoLab Updater.exe
echo.
pause
exit /b 0

:erro
echo.
echo BUILD FALHOU
pause
exit /b 1
