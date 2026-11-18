# AI design

Gemini assists the checklist. It does not decide whether a document passes.

## Extraction

`build_extraction_prompt` asks the model to read one document. The system text says the body is untrusted OCR and must not be followed as instructions. The masked text is placed between `<document_text>` tags, cut off at `AI_MAX_INPUT_CHARS` (6,000), and a closing tag inside the text is removed so the body cannot end the data block early.

The JSON object allows only:

| Field | Rule |
| --- | --- |
| `document_type_guess` | Short text or null |
| `holder_name` | Short text or null. Digits reject the whole reply |
| `date_of_birth`, `issue_date`, `expiry_date` | `yyyy-mm-dd` or null. Implausible dates become null |
| `id_last4` | Exactly four digits or null. Any other value rejects the reply |
| `issuing_authority` | Short text or null |
| `text_language` | `en`, `ta`, `mixed`, or null |
| `extraction_confidence` | `high`, `medium`, or `low` |

Unknown top-level keys are ignored. Known fields stay strict (`extra="forbid"` after the extra keys are dropped). Addresses are not requested. A saved record also stores `_meta` with the model name, the time, and the document `updated_at` from before the save. The browser does not receive `_meta`.

High or medium confidence can supply the name and dates used by the existing checks. Low confidence and an empty record keep the Step 8 heuristics. An image-quality or document-type failure is never turned into a pass. An expiry date before today fails even when no maximum age is configured.

## Explanations

`build_explanation_prompt` receives at most 25 checks that are not `pass`. Each item has an id, a document display name (or "Application"), a check code, a status, a message, and a fix suggestion. The reply is `{"items":[{"id","explanation"}],"overall_tip"}`. Explanations are capped at 220 characters and the tip at 240. Ids must be from the list, with no duplicates. URLs and markup are removed. Tamil is requested when the language is `ta`.

The result is stored at `applications.summary.ai_advice` and other summary keys are kept. Replacing, deleting, re-reading, or re-running checks removes that key.

## Privacy and injection

The API key is read from `GEMINI_API_KEY` on the server. It is not written to logs, errors, or the frontend. Logs record the document or application id, the model name, the duration, the token counts, and a status word.

Document text is data. The parser, not the model, decides which fields are kept. Model output cannot set a status, a score, a role, or any column except `uploaded_documents.extracted_fields` and `applications.summary.ai_advice`.

## Cost note from the synthetic demo

One synthetic extraction and two synthetic explanations on `gemini-3.8-flash` used about:

| Call | Time | Prompt tokens | Output tokens |
| --- | --- | --- | --- |
| Extraction | 5.3 s | 253 | 75 |
| English explanation | 6.3 s | 168 | 65 |
| Tamil explanation | 9.0 s | 168 | 74 |

Those calls used made-up text, not a citizen's document.
