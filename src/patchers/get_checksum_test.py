import re
import json
import hashlib
import binascii
from pathlib import Path

from utils.encodings import detect_file_encoding


def list_dir(path, suffix, sub):
    result = []
    path = Path(path)

    # Sorting the order of file searches for synchronized games
    for file in sorted(path.iterdir()):
        if file.is_file() and file.suffix == suffix:
            result.append(str(file))
        elif file.is_dir() and sub:
            result.extend(list_dir(file, suffix, sub))

    return result


def load_manifest(path):
    path = Path(path)

    files = []

    read = -1

    name = ""
    sub_directories = ""
    file_extension = ""

    checksum_manifest = path / "checksum_manifest.txt"

    if not checksum_manifest.exists() or not checksum_manifest.is_file():
        return files

    # Load hash calculation range from checksum_manifest
    _encoding = detect_file_encoding(checksum_manifest)
    with open(checksum_manifest, 'r', encoding=_encoding) as f:
        for line in f:
            data = line.strip()

            if data == "directory" and read <= 0:
                read = 3

            if data.startswith("name") and read != 0:
                read -= 1
                name = data.split("=")[1].strip()

            if data.startswith("sub_directories") and read != 0:
                read -= 1
                sub_directories = data.split("=")[1].strip()

            if data.startswith("file_extension") and read != 0:
                read -= 1
                file_extension = data.split("=")[1].strip()

            # Start counting files if all three parameters have been read.
            if read == 0:
                read = -1
                files += list_dir(path / name, file_extension, sub_directories == "yes")

    return files


def get_checksum_version(path):
    path = Path(path) / "launcher-settings.json"
    _encoding = detect_file_encoding(path)
    with path.open('r', encoding=_encoding) as f:
        data = json.load(f)
        version_name = data.get("version").strip().split(' ')[0]
        raw_version = data.get("rawVersion").strip()

    version = f"{version_name} {raw_version}"

    return version


def get_full_version(path):
    path = Path(path) / "launcher-settings.json"
    _encoding = detect_file_encoding(path)
    with path.open('r', encoding=_encoding) as f:
        data = json.load(f).get("version").strip()

    return data


def calc_checksum(path):
    path = Path(path)

    files = load_manifest(path)
    checksum_version = get_checksum_version(path)
    print(f"Files: {len(files)}")
    print(f"Checksum Version: {checksum_version}")

    md5 = hashlib.md5()

    for file in files:
        file_path = Path(file)
        md5.update(file_path.read_bytes())

        rel_dir = file_path.relative_to(path).as_posix()

        md5.update(rel_dir.encode("utf8"))

    md5.update(checksum_version.encode("utf8"))
    return md5.hexdigest().lower()


if __name__ == "__main__":
    paths = [
        "/mnt/GamerHomie/SteamLibrary/steamapps/common/Stellaris",
        "/mnt/InternalHomie/SteamLibrary/steamapps/common/Stellaris"
    ]

    for gamepath in paths:
        print(f"Game Path: {gamepath}")
        version = get_full_version(gamepath)
        checksum = calc_checksum(gamepath)
        print(f"Version: {version}")
        print(f"Checksum: {checksum}")
        exe = Path(gamepath) / "stellaris"
        if not exe.exists():
            exe = Path(gamepath) / "stellaris.exe"
        with open(exe, 'rb') as file:
            binary_data = file.read()

        binary_hex = binascii.hexlify(binary_data).decode()
        regex_pattern = re.compile(checksum, re.IGNORECASE)

        match = regex_pattern.search(binary_hex)

        if match:
            print("MD5 hash found in binary file!")
        else:
            print("MD5 hash not found in binary file.")
        print()
