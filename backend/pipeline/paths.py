from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
METADATA_DIR = DATA_DIR / "metadata"


def write_text_lf(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write with LF line endings on every OS, so checksums of generated files match a git checkout anywhere."""
    with path.open("w", encoding=encoding, newline="\n") as fh:
        fh.write(text)
