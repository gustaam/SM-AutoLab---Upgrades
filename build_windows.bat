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
%PYTHON% -c "import sys; raise SystemExit(0 if sys.version_info[:3] == (3, 14, 7) else 1)"
if errorlevel 1 (
    echo ERRO: este build exige exatamente Python 3.14.7.
    goto :erro
)

echo.
echo Validando versao e arquitetura consolidada...
%PYTHON% scripts\validate_architecture.py
if errorlevel 1 goto :erro
echo Validacao de arquitetura: OK
echo.

%PYTHON% -m pip install pip==26.2.1
if errorlevel 1 goto :erro
%PYTHON% -m pip install -r requirements.txt
if errorlevel 1 goto :erro
%PYTHON% -m pip check
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

%PYTHON% -c "from main import install_ui_dashboard_29917; from interface import App; from patch import aplicar_patch_ui; from main import _corrigir_historico_ilimitado, _validar_base_aplicacao, install_ui_29912, install_ui_fluent_29916; aplicar_patch_ui(App); _corrigir_historico_ilimitado(); install_ui_29912(App); install_ui_fluent_29916(App); _validar_base_aplicacao(); install_ui_dashboard_29917(App); print('Integracao consolidada: OK')"
if errorlevel 1 (
    echo ERRO: falha na integracao das camadas da base.
    goto :erro
)

powershell -NoProfile -Command "$v=(Get-Content VERSION -Raw).Trim(); $p=$v.Split('.'); if($p.Count -lt 3 -or $p.Count -gt 4){throw 'VERSION invalida'}; $b=if($p.Count -eq 4){$p[3]}else{'0'}; $t=[string]::Join([Environment]::NewLine,@('VSVersionInfo(','  ffi=FixedFileInfo(','    filevers=(__MAJOR__, __MINOR__, __PATCH__, __BUILD__),','    prodvers=(__MAJOR__, __MINOR__, __PATCH__, __BUILD__),','    mask=0x3f,','    flags=0x0,','    OS=0x40004,','    fileType=0x1,','    subtype=0x0,','    date=(0, 0)','  ),','  kids=[','    StringFileInfo([','      StringTable(''040904B0'', [','        StringStruct(''CompanyName'', ''SM AutoLab''),','        StringStruct(''FileDescription'', ''SM AutoLab''),','        StringStruct(''FileVersion'', ''__VERSION__''),','        StringStruct(''InternalName'', ''SM AutoLab''),','        StringStruct(''OriginalFilename'', ''SM AutoLab.exe''),','        StringStruct(''ProductName'', ''SM AutoLab''),','        StringStruct(''ProductVersion'', ''__VERSION__'')','      ])','    ]),','    VarFileInfo([VarStruct(''Translation'', [1033, 1200])])','  ]',')')); $t=$t.Replace('__MAJOR__',$p[0]).Replace('__MINOR__',$p[1]).Replace('__PATCH__',$p[2]).Replace('__BUILD__',$b).Replace('__VERSION__',$v); Set-Content version_info.txt $t -Encoding UTF8"
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
