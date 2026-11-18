"""One synthetic extraction and two synthetic explanations. Not used by pytest.

Run from the backend folder:
    .\\.venv\\Scripts\\python.exe scripts\\ai_live_demo.py
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.client import AIUnavailableError, complete_json
from app.ai.explanations import build_explanation_prompt, parse_explanations
from app.ai.extraction import build_extraction_prompt, parse_extraction
from app.config import settings

SAMPLE = "Name: EXAMPLE PERSON\nIssue date: 15/01/2024\nReference XXXX XXXX 1234"
CHECKS = [
    {
        "id": "check-1",
        "document_name": "Example address proof",
        "check_code": "date_validity",
        "status": "warning",
        "message": "We could not find a date.",
        "fix_suggestion": "Make sure the date is visible.",
    }
]


def _call(system: str, user: str) -> tuple[str, dict[str, int], int]:
    started = time.perf_counter()
    text, usage = complete_json(system, user)
    return text, usage, int((time.perf_counter() - started) * 1000)


def main() -> int:
    print(f"model {(settings.GEMINI_MODEL or '').strip()}")
    try:
        system, user = build_extraction_prompt("Example address proof", ["address proof"], SAMPLE)
        raw, usage, elapsed = _call(system, user)
        print("extraction_ms", elapsed)
        print("extraction_tokens", usage["prompt_tokens"], usage["output_tokens"])
        print(json.dumps(parse_extraction(raw), ensure_ascii=True))
        for language in ("en", "ta"):
            explain_system, explain_user = build_explanation_prompt(CHECKS, language)
            raw, usage, elapsed = _call(explain_system, explain_user)
            print(f"explanation_{language}_ms", elapsed)
            print(f"explanation_{language}_tokens", usage["prompt_tokens"], usage["output_tokens"])
            print(json.dumps(parse_explanations(raw, {"check-1"}), ensure_ascii=True))
    except (AIUnavailableError, Exception) as exc:
        category = getattr(exc, "category", None) or type(exc).__name__
        print("failure")
        print(category)
        return 1
    print("success")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
