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


def normalise_text(text: str) -> str:
    """Same line endings and no surrounding blank space, so neither changes `text_fingerprint()`."""
    return text.replace("\r\n", "\n").strip()


def text_fingerprint(text: str) -> str:
    """
    Identifies a text's content, so a changed text can be told apart from one already seen.
    Empty if there is no text.
    """
    normalised = normalise_text(text)

    if not normalised:
        return ""

    return hashlib.sha256(normalised.encode("utf-8-sig")).hexdigest()
