#!/bin/bash

set -e
set -o pipefail

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

SRC_DIR="$PROJECT_ROOT/src"
VENV_DIR="$PROJECT_ROOT/venv-stellaris-checksum-patcher"
PYPROJECT_FILE="$PROJECT_ROOT/pyproject.toml"
MAIN_FILE="$SRC_DIR/main.py"
PYTHON_BIN="python3"
USE_UV=false

check_dependencies() {
    if ! command -v "$PYTHON_BIN" &>/dev/null; then
        printf "Error: Python3 is not installed or not found in PATH.\n" >&2
        return 1
    fi

    if ! "$PYTHON_BIN" -c "import venv" &>/dev/null; then
        printf "Error: Python3 venv module is missing. Install it and try again.\n" >&2
        return 1
    fi

    if command -v uv &>/dev/null; then
        printf "uv found. Using uv for package management.\n"
        USE_UV=true
    else
        printf "uv not found. Using pip for package management.\n"
    fi
}

create_or_find_virtualenv() {
    if [[ -d "$VENV_DIR" ]]; then
        printf "Virtual environment already exists.\n"
    else
        printf "Creating virtual environment in %s\n" "$VENV_DIR"
        if [ "$USE_UV" = true ]; then
            if ! uv venv --python "$PYTHON_BIN" "$VENV_DIR"; then
                printf "Error: Failed to create virtual environment with uv.\n" >&2
                return 1
            fi
        else
            if ! "$PYTHON_BIN" -m venv "$VENV_DIR"; then
                printf "Error: Failed to create virtual environment with python -m venv.\n" >&2
                return 1
            fi
        fi
    fi
}

activate_virtualenv() {
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
}

sync_dependencies() {
    if [[ ! -f "$PYPROJECT_FILE" ]]; then
        printf "Error: pyproject.toml not found in the current directory.\n" >&2
        return 1
    fi

    printf "Ensuring dependencies from %s are up to date...\n" "$PYPROJECT_FILE"

    # Change to project root for dependency installation
    cd "$PROJECT_ROOT"

    if [ "$USE_UV" = true ]; then
        if ! uv pip install --upgrade pip setuptools; then
            printf "Error: Failed to upgrade pip and setuptools using uv.\n" >&2
            return 1
        fi
        if ! uv sync --active; then
            printf "Error: Failed to sync dependencies using uv.\n" >&2
            return 1
        fi
        # Install the local project in editable mode without reinstalling dependencies.
        if ! uv pip install --no-deps -e .; then 
            printf "Error: Failed to install the project in editable mode using uv.\n">&2
            return 1
        fi
    else
        if ! python -m pip install --upgrade pip setuptools; then
            printf "Error: Failed to upgrade pip and setuptools using pip.\n" >&2
            return 1
        fi
        if ! python -m pip install .; then
            printf "Error: Failed to install dependencies from pyproject.toml using pip.\n" >&2
            return 1
        fi
    fi
}

run_project() {
    if [[ ! -f "$MAIN_FILE" ]]; then
        printf "Error: Main script not found at %s\n" "$MAIN_FILE" >&2
        return 1
    fi

    printf "Running the project...\n"
    if ! python "$MAIN_FILE"; then
        printf "Error: Failed to run the Python project.\n" >&2
        return 1
    fi
}

main() {
    check_dependencies
    create_or_find_virtualenv
    activate_virtualenv
    sync_dependencies
    run_project
    printf "\nScript finished successfully.\n"
}

main
