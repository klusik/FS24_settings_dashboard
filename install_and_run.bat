@echo off
setlocal EnableExtensions

set "MIN_PYTHON=3.10"
set "INSTALL_PYTHON=3.12"
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_PATH=%SCRIPT_DIR%MS_Setup.pyw"

title MSFS 2024 Settings Dashboard Launcher

if not exist "%SCRIPT_PATH%" (
    echo ERROR: MS_Setup.pyw was not found next to this batch file.
    echo.
    echo Keep install_and_run.bat and MS_Setup.pyw in the same folder.
    pause
    exit /b 1
)

call :find_python
if "%PYTHON_OK%"=="1" goto run_app

echo Python %MIN_PYTHON% or newer was not found.
echo Installing Python %INSTALL_PYTHON% for the current Windows user...
echo.

call :install_python
if errorlevel 1 (
    echo.
    echo ERROR: Python installation failed.
    echo Please install Python %MIN_PYTHON% or newer from https://www.python.org/downloads/windows/
    echo Then run this file again.
    pause
    exit /b 1
)

call :find_python
if not "%PYTHON_OK%"=="1" (
    echo.
    echo ERROR: Python was installed, but this launcher still cannot find Python %MIN_PYTHON% or newer.
    echo Try closing this window and running install_and_run.bat again.
    pause
    exit /b 1
)

:run_app
echo Starting Microsoft Flight Simulator 2024 Settings Dashboard...
set "RUN_EXE=%PYTHON_EXE%"
if /I "%PYTHON_EXE:~-10%"=="python.exe" (
    set "PYTHONW_EXE=%PYTHON_EXE:~0,-10%pythonw.exe"
    if exist "%PYTHONW_EXE%" set "RUN_EXE=%PYTHONW_EXE%"
)
start "" "%RUN_EXE%" "%SCRIPT_PATH%"
exit /b 0

:find_python
set "PYTHON_OK=0"
set "PYTHON_EXE="

for %%C in (
    "py -%MIN_PYTHON%"
    "py -3"
    "python"
    "python3"
) do (
    if not defined PYTHON_EXE (
        call :check_candidate "%%~C"
    )
)

for %%P in (
    "%LocalAppData%\Programs\Python\Python312\python.exe"
    "%LocalAppData%\Programs\Python\Python311\python.exe"
    "%LocalAppData%\Programs\Python\Python310\python.exe"
) do (
    if not defined PYTHON_EXE (
        if exist "%%~P" call :check_exe_path "%%~P"
    )
)
exit /b 0

:check_candidate
set "CANDIDATE=%~1"

%CANDIDATE% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 exit /b 0

for /f "usebackq delims=" %%P in (`%CANDIDATE% -c "import sys; print(sys.executable)" 2^>nul`) do (
    set "PYTHON_EXE=%%P"
)

if defined PYTHON_EXE set "PYTHON_OK=1"
exit /b 0

:check_exe_path
set "CANDIDATE_EXE=%~1"

"%CANDIDATE_EXE%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 exit /b 0

for /f "usebackq delims=" %%P in (`"%CANDIDATE_EXE%" -c "import sys; print(sys.executable)" 2^>nul`) do (
    set "PYTHON_EXE=%%P"
)

if defined PYTHON_EXE set "PYTHON_OK=1"
exit /b 0

:install_python
where winget >nul 2>nul
if not errorlevel 1 (
    winget install --id Python.Python.%INSTALL_PYTHON% --exact --scope user --accept-package-agreements --accept-source-agreements
    if not errorlevel 1 exit /b 0
)

echo winget could not install Python. Trying the official Python installer fallback...

set "PYTHON_INSTALLER=%TEMP%\python-3.12.10-amd64.exe"
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe' -OutFile $env:PYTHON_INSTALLER -UseBasicParsing; exit 0 } catch { Write-Host $_.Exception.Message; exit 1 }"
if errorlevel 1 exit /b 1

"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_tcltk=1 Include_pip=1
if errorlevel 1 exit /b 1

exit /b 0
