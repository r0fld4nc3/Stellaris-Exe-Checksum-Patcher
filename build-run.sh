#!/bin/bash

set -e
set -o pipefail

SRC_DIR="./src"
VENV_DIR="./venv-stellaris-checkum-patcher"
PYPROJECT_FILE="./pyproject.toml"
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

    # Check if uv is installed
    if command -v uv &>/dev/null; then
        printf "uv found. Using uv for package management.\n"
        USE_UV=true
    else
        printf "uv not found. Using pip for package management.\n"
    fi
}

create_virtualenv() {
    if [[ -d "$VENV_DIR" ]]; then
        printf "Virtual environment already exists. Skipping creation.\n"
    else
        printf "Creating virtual environment in %s\n" "$VENV_DIR"
        if "$USE_UV"; then
            # Use uv to create the virtual environment
            if ! uv venv --python "$PYTHON_BIN" "$VENV_DIR"; then
                printf "Error: Failed to create virtual environment with uv.\n" >&2
                return 1
            fi
        else
            # Use standard venv
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
    # After activation, ensure the correct python/pip is used.
    # uv often installs its own shim or makes its commands available.
    # If uv is active, it might override python/pip.
    # We'll rely on uv's integration after activation.
}

install_dependencies() {
    if [[ ! -f "$PYPROJECT_FILE" ]]; then
        printf "Error: pyproject.toml not found in the current directory.\n" >&2
        return 1
    fi

    printf "Installing dependencies from %s\n" "$PYPROJECT_FILE"

    if "$USE_UV"; then
        # uv to install dependencies
        if ! uv pip install --upgrade pip setuptools; then
            printf "Error: Failed to upgrade pip and setuptools using uv.\n" >&2
            return 1
        fi
        if ! uv pip install .; then
            printf "Error: Failed to install dependencies from pyproject.toml using uv.\n" >&2
            return 1
        fi
    else
        # Use standard pip
        if ! python3 -m pip install --upgrade pip setuptools; then
            printf "Error: Failed to upgrade pip and setuptools using pip.\n" >&2
            return 1
        fi
        if ! python3 -m pip install .; then
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
    # Use the python interpreter from the activated virtual environment
    if ! python "$MAIN_FILE"; then # Use 'python' after activation
        printf "Error: Failed to run the Python project.\n" >&2
        return 1
    fi
}

main() {
    check_dependencies || return 1
    create_virtualenv || return 1
    activate_virtualenv || return 1
    install_dependencies || return 1
    run_project || return 1
}

main
