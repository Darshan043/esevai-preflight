"""Print the extraction and explanation prompts built from synthetic text only.

Run from the backend folder:
    .\\.venv\\Scripts\\python.exe scripts\\ai_prompt_preview.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.explanations import build_explanation_prompt
from app.ai.extraction import build_extraction_prompt


def main() -> None:
    system, user = build_extraction_prompt(
        "Example address proof",
        ["address proof"],
        "Name: EXAMPLE PERSON\nIssue date: 2024-01-15\nReference XXXX XXXX 1234",
    )
    print("EXTRACTION SYSTEM")
    print(system)
    print("EXTRACTION USER")
    print(user)
    explain_system, explain_user = build_explanation_prompt(
        [
            {
                "id": "check-1",
                "document_name": "Example address proof",
                "check_code": "date_validity",
                "status": "warning",
                "message": "We could not find a date.",
                "fix_suggestion": "Make sure the date is visible.",
            }
        ],
        "en",
    )
    print("EXPLANATION SYSTEM")
    print(explain_system)
    print("EXPLANATION USER")
    print(explain_user)


if __name__ == "__main__":
    main()
