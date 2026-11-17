"""Read one local file and print quality numbers plus masked text.

Usage, from the backend folder:
    python scripts/ocr_demo.py <path-to-local-file>

Nothing is saved. The printed text already has ID numbers hidden.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.processing.loader import DocumentUnreadableError
from app.processing.pipeline import process_document


def guess_mime(path: Path, content: bytes) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".pdf":
        return "application/pdf"
    if content.startswith(b"%PDF"):
        return "application/pdf"
    if content.startswith(b"\x89PNG"):
        return "image/png"
    if content.startswith(b"\xff\xd8"):
        return "image/jpeg"
    return "application/octet-stream"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/ocr_demo.py <path-to-local-file>", file=sys.stderr)
        return 1
    path = Path(sys.argv[1])
    if not path.is_file():
        print("That file was not found.", file=sys.stderr)
        return 1
    content = path.read_bytes()
    try:
        result = process_document(content, guess_mime(path, content))
    except DocumentUnreadableError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    metrics = result["quality_metrics"]
    print(json.dumps(metrics, indent=2))
    print(result["ocr_text_masked"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
