"""Remove applications that have not been updated within DATA_RETENTION_DAYS.

Dry-run is the default. Pass --apply to delete. Prints counts only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.retention import cleanup_expired  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Count or delete applications older than DATA_RETENTION_DAYS.")
    parser.add_argument("--apply", action="store_true", help="Delete expired applications. Default is dry-run.")
    args = parser.parse_args()
    result = cleanup_expired(dry_run=not args.apply)
    mode = "apply" if args.apply else "dry-run"
    print(
        f"cleanup {mode} days={result['days']} "
        f"applications={result['applications']} files={result['files']} "
        f"deleted_applications={result['deleted_applications']} "
        f"deleted_files={result['deleted_files']} skipped={result['skipped_applications']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
