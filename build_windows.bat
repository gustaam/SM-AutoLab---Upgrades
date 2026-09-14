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
echo Verificando codigo-fonte da versao atual...
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
if not exist "atualizacao.py" (
    echo ERRO: atualizacao.py nao encontrado.
    goto :erro
)
if not exist "patch_base.py" (
    echo ERRO: patch_base.py nao encontrado.
    goto :erro
)
if not exist "patch_arquivos.py" (
    echo ERRO: patch_arquivos.py nao encontrado.
    goto :erro
)
if not exist "patch_ajustes.py" (
    echo ERRO: patch_ajustes.py nao encontrado.
    goto :erro
)
if not exist "version_info_template.txt" (
    echo ERRO: version_info_template.txt nao encontrado.
    goto :erro
)
%SystemRoot%\System32\findstr.exe /c:"def aplicar_patch_base" patch_base.py >nul
if errorlevel 1 (
    echo ERRO: patch_base.py nao expoe a camada base neutra.
    goto :erro
)
%SystemRoot%\System32\findstr.exe /c:"def aplicar_patch_arquivos" patch_arquivos.py >nul
if errorlevel 1 (
    echo ERRO: patch_arquivos.py nao expoe a camada de Arquivos neutra.
    goto :erro
)
%SystemRoot%\System32\findstr.exe /c:"def aplicar_patch_ajustes" patch_ajustes.py >nul
if errorlevel 1 (
    echo ERRO: patch_ajustes.py nao expoe a camada de ajustes.
    goto :erro
)
%SystemRoot%\System32\findstr.exe /c:"from patch_base import aplicar_patch_base" main.py >nul
if errorlevel 1 (
    echo ERRO: main.py nao esta usando a camada base atual.
    goto :erro
)
%SystemRoot%\System32\findstr.exe /c:"from patch_arquivos import aplicar_patch_arquivos" main.py >nul
if errorlevel 1 (
    echo ERRO: main.py nao esta usando a camada de Arquivos atual.
    goto :erro
)
%SystemRoot%\System32\findstr.exe /c:"from patch_ajustes import aplicar_patch_ajustes" main.py >nul
if errorlevel 1 (
    echo ERRO: main.py nao esta usando a camada de ajustes atual.
    goto :erro
)
echo Validacao do codigo-fonte: OK
echo.

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
%PYTHON% -m pip install pyinstaller==6.22.2
if errorlevel 1 goto :erro

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "*.spec" del /q "*.spec"
if exist "version_info.txt" del /q "version_info.txt"

%PYTHON% -m compileall -q .
if errorlevel 1 (
    echo ERRO: falha na validacao da sintaxe Python.
    goto :erro
)

%PYTHON% -c "from interface import App; from patch_base import aplicar_patch_base; from patch_arquivos import aplicar_patch_arquivos; from patch_ajustes import aplicar_patch_ajustes; from main import _validar_base_aplicacao; aplicar_patch_base(App); aplicar_patch_arquivos(App); aplicar_patch_ajustes(App); _validar_base_aplicacao(); print('Integracao da base: OK')"
if errorlevel 1 (
    echo ERRO: falha na integracao das camadas da base.
    goto :erro
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$v=(Get-Content VERSION -Raw).Trim(); $p=$v.Split('.'); if($p.Count -ne 3){throw 'VERSION invalida'}; $t=Get-Content version_info_template.txt -Raw; $t=$t.Replace('__MAJOR__',$p[0]).Replace('__MINOR__',$p[1]).Replace('__PATCH__',$p[2]).Replace('__VERSION__',$v); Set-Content version_info.txt $t -Encoding UTF8"
if errorlevel 1 goto :erro

if not exist "version_info.txt" (
    echo ERRO: nao foi possivel gerar os metadados do executavel.
    goto :erro
)

echo.
echo Gerando SM AutoLab v!APP_VERSION!...
%PYTHON% -m PyInstaller --noconfirm --clean --onefile --windowed --name "SM AutoLab" --noupx --version-file "version_info.txt" --collect-submodules selenium --collect-data selenium --collect-data customtkinter --icon "SM AutoLab.ico" --add-data "SM AutoLab.ico;." --add-data "assets;assets" --add-data "VERSION;." main.py
if errorlevel 1 goto :erro

if not exist "dist\SM AutoLab.exe" (
    echo ERRO: executavel principal nao foi gerado.
    goto :erro
)

echo.
echo BUILD CONCLUIDO:
echo dist\SM AutoLab.exe
echo.
pause
exit /b 0

:erro
echo.
echo BUILD FALHOU
pause
exit /b 1
