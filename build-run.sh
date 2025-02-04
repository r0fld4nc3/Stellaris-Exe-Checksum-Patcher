#!/bin/bash

set -e
set -o pipefail

SRC_DIR="./src"
VENV_DIR="./venv-stellaris-checkum-patcher"
PYPROJECT_FILE="./pyproject.toml"
MAIN_FILE="$SRC_DIR/main.py"
PYTHON_BIN="python3"

check_dependencies() {
    if ! command -v "$PYTHON_BIN" &>/dev/null; then
        printf "Error: Python3 is not installed or not found in PATH.\n" >&2
        return 1
    fi

    if ! "$PYTHON_BIN" -c "import venv" &>/dev/null; then
        printf "Error: Python3 venv module is missing. Install it and try again.\n" >&2
        return 1
    fi
}

create_virtualenv() {
    if [[ -d "$VENV_DIR" ]]; then
        printf "Virtual environment already exists. Skipping creation.\n"
    else
        printf "Creating virtual environment in %s\n" "$VENV_DIR"
        if ! "$PYTHON_BIN" -m venv "$VENV_DIR"; then
            printf "Error: Failed to create virtual environment.\n" >&2
            return 1
        fi
    fi
}

activate_virtualenv() {
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
}

install_dependencies() {
    if [[ ! -f "$PYPROJECT_FILE" ]]; then
        printf "Error: pyproject.toml not found in the current directory.\n" >&2
        return 1
    fi

    printf "Installing dependencies from %s\n" "$PYPROJECT_FILE"
    if ! python3 -m pip install --upgrade pip setuptools; then
        printf "Error: Failed to upgrade pip and setuptools.\n" >&2
        return 1
    fi

    if ! python3 -m pip install .; then
        printf "Error: Failed to install dependencies from pyproject.toml.\n" >&2
        return 1
    fi
}

run_project() {
    if [[ ! -f "$MAIN_FILE" ]]; then
        printf "Error: Main script not found at %s\n" "$MAIN_FILE" >&2
        return 1
    fi

    printf "Running the project...\n"
    if ! python3 "$MAIN_FILE"; then
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
