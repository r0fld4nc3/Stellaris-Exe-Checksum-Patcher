@echo off
setlocal enabledelayedexpansion

set "SRC_DIR=.\src"
set "VENV_DIR=.\venv-stellaris-checkum-patcher"
set "PYPROJECT_FILE=.\pyproject.toml"
set "MAIN_FILE=%SRC_DIR%\main.py"
set "PYTHON_BIN=python"

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

REM Create virtual environment if it doesn't exist
if exist "%VENV_DIR%" (
    echo Virtual environment already exists. Skipping creation.
) else (
    echo Creating virtual environment in %VENV_DIR%
    %PYTHON_BIN% -m venv "%VENV_DIR%"
    if %ERRORLEVEL% neq 0 (
        echo Error: Failed to create virtual environment.
        exit /b 1
    )
)

REM Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to activate virtual environment.
    exit /b 1
)

REM Install dependencies
if not exist "%PYPROJECT_FILE%" (
    echo Error: pyproject.toml not found in the current directory.
    exit /b 1
)

echo Installing dependencies from %PYPROJECT_FILE%
python -m pip install --upgrade pip setuptools
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to upgrade pip and setuptools.
    exit /b 1
)

python -m pip install .
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to install dependencies from pyproject.toml.
    exit /b 1
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

exit /b 0
