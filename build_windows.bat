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
%SystemRoot%\System32\findstr.exe /c:"tkcalendar" interface.py >nul
if not errorlevel 1 (
    echo ERRO: interface.py ainda contem dependencia externa tkcalendar.
    goto :erro
)
for %%F in (main.py interface.py app.py automacao.py config.py atualizacao.py patch.py VERSION version_info_template.txt) do (
    if not exist "%%F" (
        echo ERRO: %%F nao encontrado.
        goto :erro
    )
)
%SystemRoot%\System32\findstr.exe /c:"from patch import aplicar_patch_ui" main.py >nul
if errorlevel 1 (
    echo ERRO: main.py nao usa a entrada consolidada patch.py.
    goto :erro
)
%SystemRoot%\System32\findstr.exe /c:"def aplicar_patch_ui" patch.py >nul
if errorlevel 1 (
    echo ERRO: patch.py nao expoe aplicar_patch_ui.
    goto :erro
)
%SystemRoot%\System32\findstr.exe /c:"class StartupSplash" main.py >nul
if errorlevel 1 (
    echo ERRO: main.py nao contem o splash consolidado.
    goto :erro
)
%SystemRoot%\System32\findstr.exe /c:"class Resultados" app.py >nul
if errorlevel 1 (
    echo ERRO: app.py nao contem o modulo consolidado de resultados.
    goto :erro
)
%SystemRoot%\System32\findstr.exe /c:"def carregar_codigos" app.py >nul
if errorlevel 1 (
    echo ERRO: app.py nao contem o leitor de planilhas consolidado.
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

%PYTHON% -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 (
    echo ERRO: falha nos testes automatizados.
    goto :erro
)

%PYTHON% -c "from interface import App; from patch import aplicar_patch_ui; from main import _corrigir_historico_ilimitado, _validar_base_aplicacao, install_ui_29912; aplicar_patch_ui(App); _corrigir_historico_ilimitado(); install_ui_29912(App); _validar_base_aplicacao(); print('Integracao consolidada: OK')"
if errorlevel 1 (
    echo ERRO: falha na integracao das camadas da base.
    goto :erro
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$v=(Get-Content VERSION -Raw).Trim(); $p=$v.Split('.'); if($p.Count -lt 3 -or $p.Count -gt 4){throw 'VERSION invalida'}; $t=Get-Content version_info_template.txt -Raw; $b=if($p.Count -eq 4){$p[3]}else{'0'}; $t=$t.Replace('__MAJOR__',$p[0]).Replace('__MINOR__',$p[1]).Replace('__PATCH__',$p[2]).Replace('__BUILD__',$b).Replace('__VERSION__',$v); Set-Content version_info.txt $t -Encoding UTF8"
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
