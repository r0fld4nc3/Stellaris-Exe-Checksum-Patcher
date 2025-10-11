from pathlib import Path

import chardet

from conf_globals import LOG_LEVEL
from logger import create_logger

log = create_logger("Encodings", LOG_LEVEL)

# https://www.ibm.com/docs/en/zos-connect/zosconnect/3.0?topic=SS4SVW_3.0.0%2Fdesigning%2Fccsid_list.htm
# https://uic.io/en/charset/supported_list/
ENCODINGS = [
    "utf-8",
    "utf-8-sig",  # UTF-8 with BOM
    "utf-16",
    "utf-16-le",
    "utf-16-be",
    "cp1252",  # Windows default
    "iso-8859-1",  # Latin-1
    "cp437",  # Original IBM PC character set
    "cp850",  # MS-DOS Western European
    "gbk",  # Simplified Chinese
    "big5",  # Traditional Chinese
    "euc-jp",  # Japanese
    "euc-kr",  # Korean
    "cp1256",  # Arabic
    "cp1251",  # Cyrillic
    "koi8-r",  # Russian
    "shift_jis",  # Japanese
]


def detect_file_encoding(fp, min_confidence=0.7, default_encoding="utf-8", read_size=4096):
    """
    Detect the encoding of a file with the highest confidence.

    Args:
        fp: Path to the file (str or Path object)
        min_confidence: Minimum confidence threshold to accept detected encoding
        default_encoding: Fallback encoding if detection fails or confidence is low
        read_size: Number of bytes to read for detection

    Returns:
        The detected encoding as a string, or default_encoding if detection fails
    """

    log.debug(f"Detect encoding: {str(fp)}")

    if not isinstance(fp, Path):
        fp = Path(fp)

    if not fp.exists():
        log.error(f"File does not exist: {str(fp)}")
        return default_encoding

    if fp.stat().st_size == 0:
        log.debug(f"File is empty: {str(fp)}")
        return default_encoding

    try:
        with open(fp, "rb") as f:
            # For small files, read the entire file
            if fp.stat().st_size <= read_size:
                raw_data = f.read()
            else:
                # For larger files, read from beginning, middle, and end for better detection
                beginning = f.read(read_size // 3)
                f.seek(fp.stat().st_size // 2)
                middle = f.read(read_size // 3)
                f.seek(-min(read_size // 3, fp.stat().st_size), 2)  # 2 means from end of file
                end = f.read(read_size // 3)
                raw_data = beginning + middle + end

            result = chardet.detect(raw_data)
            _confidence = result.get("confidence", 0)
            _encoding = result.get("encoding")

            if _encoding is None:
                log.warning(f"No encoding detected for {str(fp)}")
                return default_encoding

            _encoding = _encoding.lower()

            # Special cases
            if _encoding == "ascii":
                # ASCII is a subset of UTF-8
                log.debug(f"Detected encoding {_encoding}, using utf-8.")
                return "utf-8"

            if _confidence >= min_confidence:
                log.debug(f"Detected encoding '{_encoding}' with confidence {_confidence:.2f}")
                return _encoding
            else:
                log.debug(f"Low confidence ({_confidence:.2f}) for encoding '{_encoding}', using default")
                return default_encoding

    except Exception as e:
        log.error(f"Error during encoding detection for {str(fp)}: {e}")

    log.debug(f"No specific encoding detected with sufficient confidence, using {default_encoding}")
    return default_encoding


def safe_read_file_encode(fp: Path, default_encoding="utf-8", min_confidence=0.7, read_size=4096):
    """
    Safely read a file attempting proper encoding detection and fallbacks

    Args:
        fp: Path to the file to read
        default_encoding: Default encoding to attempt if detection fails
        min_confidence: Minimum confidence threshold for encoding detection
        read_size: Number of bytes to read for encoding detection

    Returns:
        The file contents as a string, or None if reading fails
    """

    global ENCODINGS

    if not isinstance(fp, Path):
        fp = Path(fp)

    if not fp.exists():
        log.error(f"File does not exist: {str(fp)}")
        return None

    if fp.stat().st_size == 0:
        log.debug(f"File is empty: {str(fp)}")
        return ""

    detected_encoding = detect_file_encoding(
        fp, min_confidence=min_confidence, default_encoding=default_encoding, read_size=read_size
    )

    # Create a prioritized list of encodings to try
    encodings_to_try = [detected_encoding]

    # Build a list of encodings to try with the detected one as highest priority
    for enc in ENCODINGS:
        if enc.lower() != detected_encoding.lower():
            encodings_to_try.append(enc)

    # Attempt each encoding
    last_exception = None
    for enc in encodings_to_try:
        try:
            with open(fp, "r", encoding=enc) as f:
                content = f.read()
                log.debug(f"Successfully read file with encoding {enc}")
                return content
        except UnicodeDecodeError as e:
            last_exception = e
            log.debug(f"Failed to decode with '{enc}': {e}")
        except Exception as e:
            last_exception = e
            log.error(f"Error reading file with '{enc}': {e}")

    # All encodings have failed
    log.error(f"Failed to read file {str(fp)} with any known encoding. Last error: {last_exception}")
    return None
