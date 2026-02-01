@echo off
setlocal enabledelayedexpansion

REM Get the project root directory
set "SCRIPT_DIR=%~dp0"
REM Navigate ip one directory to get PROJECT_ROOT
for %%i in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fi"

set "SRC_DIR=%PROJECT_ROOT%\src"
set "VENV_DIR=%PROJECT_ROOT%\venv-stellaris-checksum-patcher"
set "PYPROJECT_FILE=%PROJECT_ROOT%\pyproject.toml"
set "MAIN_FILE=%SRC_DIR%\main.py"
set "PYTHON_BIN=python"
set "USE_UV=false"

REM Check if Python is installed
where %PYTHON_BIN% >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Python is not installed or not found in PATH.
    exit /b 1
)

REM Check if Python venv module is available
%PYTHON_BIN% -c "import venv" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Python venv module is missing. Install it and try again.
    exit /b 1
)

REM Check if uv is installed
where uv >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo uv found. Using uv for package management.
    set "USE_UV=true"
) else (
    echo uv not found. Using pip for package management.
)

REM Create virtual environment if it doesn't exist
if exist "%VENV_DIR%" (
    echo Virtual environment already exists.
) else (
    echo Creating virtual environment in %VENV_DIR%
    if "%USE_UV%"=="true" (
        uv venv --python %PYTHON_BIN% "%VENV_DIR%"
        if !ERRORLEVEL! neq 0 (
            echo Error: Failed to create virtual environment with uv.
            exit /b 1
        )
    ) else (
        %PYTHON_BIN% -m venv "%VENV_DIR%"
        if !ERRORLEVEL! neq 0 (
            echo Error: Failed to create virtual environment with python -m venv.
            exit /b 1
        )
    )
)

REM Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to activate virtual environment.
    exit /b 1
)

REM Change to project root for dependency installation
cd /d "%PROJECT_ROOT%"

echo Ensuring dependencies from %PYPROJECT_FILE% are up to date...
if "%USE_UV%"=="true" (
    REM Upgrade pip and setuptools
    uv pip install --upgrade pip setuptools
    if !ERRORLEVEL! neq 0 (
        echo Error: Failed to upgrade pip and setuptools using uv.
        exit /b 1
    )
    REM Sync dependencies into the active environment
    uv sync --active --no-group dev
    if !ERRORLEVEL! neq 0 (
        echo Error: Failed to sync dependencies using uv.
        exit /b 1
    )
    REM Install the local project in editable mode
    uv pip install --no-deps -e .
    if !ERRORLEVEL! neq 0 (
        echo Error: Failed to install project in editable mode using uv.
        exit /b 1
    )
) else (
    REM Use standard pip to install/sync dependencies
    python -m pip install --upgrade pip setuptools
    if !ERRORLEVEL! neq 0 (
        echo Error: Failed to upgrade pip and setuptools using pip.
        exit /b 1
    )
    python -m pip install .
    if !ERRORLEVEL! neq 0 (
        echo Error: Failed to install dependencies from pyproject.toml using pip.
        exit /b 1
    )
)

REM Run the project
if not exist "%MAIN_FILE%" (
    echo Error: Main script not found at %MAIN_FILE%
    exit /b 1
)

echo Running the project...
python "%MAIN_FILE%"
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to run the Python project.
    exit /b 1
)

echo.
echo Script finished successfully.
exit /b 0
