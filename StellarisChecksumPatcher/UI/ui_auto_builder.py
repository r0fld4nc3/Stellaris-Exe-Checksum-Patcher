# Install PySide6 and/or PySide
# Navigate to Python installation, Lib\site-packages\PySide6
# Open cmd in that folder and run
# uic -g python "D:\PATH\src\ui\SuikoAssetCreatorUI.ui" -o "D:\PATH\src\ui\SuikoAssetCreatorUI.py"

import os
import sys
import dotenv
import pathlib
import subprocess

# Needs a .env
# Create a .env in the same directory as the UI folder, with the CONVERTER_PATH = ""entry.
# This entry points to the folder where the converter for .ui files is.
env_file = dotenv.find_dotenv('.env')
if not env_file:
    print("ERROR: Unable to find .env file.")
    sys.exit(1)

dotenv.load_dotenv(env_file)

python_path = os.getenv("CONVERTER_PATH")

def main():
    converter_path = python_path
    cwd = pathlib.Path(__file__).parent.parent / "ui"

    ui_file_path = cwd / "StellarisChecksumPatcherUI.ui"
    output = cwd / "StellarisChecksumPatcherUI.py"

    outputs = [(ui_file_path, output)]

    for conv in outputs:
        _fp = conv[0]
        _o = conv[1]
        command = f"uic -g python \"{_fp}\" -o \"{_o}\""
        print(command)
        subprocess.call(command, shell=True, cwd=converter_path)


if __name__ == "__main__":
    main()
