import hashlib
from pathlib import Path


def calc_file_hash(path: str | Path) -> str:
    if not isinstance(path, Path):
        file_path = Path(path)
    else:
        file_path = path

    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()
