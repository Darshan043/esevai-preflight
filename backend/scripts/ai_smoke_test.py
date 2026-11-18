"""One tiny live call. Prints the model, success or failure, and a short error category.

Run from the backend folder:
    .\\.venv\\Scripts\\python.exe scripts\\ai_smoke_test.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.client import AIUnavailableError, complete_json
from app.config import settings

# Ten tokens came back as HTTP 200 with no reply text. This cap is only for
# the smoke call and leaves room for a short JSON "OK".
SMOKE_MAX_OUTPUT_TOKENS = 1024


def smoke_outcome(text: str) -> str:
    """Classify a completed reply. An empty HTTP 200 is never called a network error."""
    if not text or not text.strip():
        return "empty_response"
    if "OK" in text.upper():
        return "success"
    return "unexpected_response"


def main() -> int:
    model = (settings.GEMINI_MODEL or "").strip() or "gemini-3.8-flash"
    print(f"model {model}")
    try:
        text, _usage = complete_json(
            "Reply with JSON only.",
            "Reply with the single word OK",
            max_tokens=SMOKE_MAX_OUTPUT_TOKENS,
        )
    except AIUnavailableError as exc:
        print("failure")
        print(exc.category)
        return 1
    outcome = smoke_outcome(text)
    if outcome == "success":
        print("success")
        return 0
    print("failure")
    print(outcome)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
