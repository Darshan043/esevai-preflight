# Admin guide

This assistant is not the official e-Sevai portal. Use the admin dashboard to describe a service and the documents a citizen should bring. The checks run from this configuration, so an invalid rule must never be saved.

Promote an admin only with `supabase/scripts/promote_admin.sql`. The role is read from the `profiles` table on the server. Hiding the Admin link does not protect the API.

## Add a new service

1. Sign in with an admin account and open **Services**.
2. Choose **New service**. Enter the English name, optional Tamil name, a slug such as `income-certificate-demo`, and a short description. Leave **Active** and **Verified** off until the list is ready. Save.
3. Add each required document. For a photograph, use **Photo-type document (no text checks)** so keywords and name matching stay off. For a paper document, add English and Tamil keywords, tick Name / ID number / Date if those details should be present, and set quality rules.
4. Set accepted formats (jpg, jpeg, png, pdf), a maximum size of 1–5 MB, and optional validity in days.
5. Reorder the list with **Up** and **Down**. Citizens see this order.
6. Test with sample documents as a citizen: keep the service inactive so it stays off `/services`, or use a private draft copy.
7. Compare the list with the official e-Sevai portal. Only then tick **Verified**. The confirmation reads: "I have checked this document list against the official e-Sevai portal".
8. Tick **Active** so the service appears on `/services`. Open **Open citizen view** to confirm.

## What each rule means

These are application settings, not official government rules. Details are in [validation-rules.md](validation-rules.md).

- **Minimum width / height** – warn if the image is smaller.
- **Minimum sharpness** – fail if the photo is too blurry.
- **Brightness range** – warn if the page is too dark or too bright. Maximum must be greater than minimum.
- **ID number pattern** – a Python regular expression such as `^[0-9]{12}$`. Nested patterns like `(a+)+` are rejected because they can hang the server. Use **Test pattern** in the form to try sample text in the browser; the server still checks Python safety on save.
- **Maximum age (days)** – fail if the newest date on the page is older than this (together with **Validity days**).
- **Compare name with other documents** – when several documents tick this, guessed names are compared.
- **Keywords** – words that should appear so the engine can tell the document type.
- **Required fields** – look for a name, an ID number, and/or a date.
- **Photo-type** – no keywords and no required fields. ID pattern and name matching must stay off.

Unknown extra keys in `rules` are rejected. Saving a seeded Community Certificate document will drop leftover keys such as `fields_are_draft`.

## Locks

- **Slug** – can change only while the service has zero applications. After that you get `slug is locked once applications exist`.
- **Document code** – can change only while no file has been uploaded for that item.
- **Delete service** – only if it has never been used. Otherwise deactivate it. The server returns `This service has been used – deactivate it instead`.
- **Delete document** – only if no uploads reference it. Otherwise deactivate it.
- **Duplicate** – copies the checklist into a new slug. The copy is always inactive and unverified. The description is prefixed with `DRAFT – verify against the official e-Sevai portal.`

Deactivating a service hides it from `/services` and blocks **Start a new check**. Existing applications still open as history.

## Statistics

Open **Overview** for totals, the Ready / Almost ready / Not ready split, top failure reasons, per-service numbers, and a bar of applications created each day. **Recent checks** shows the same safe columns with pagination.

Statistics reflect current data; validation results are replaced whenever a check is re-run.

Rows are capped (about 5,000). People are shown as `User #` plus six characters of a hash of the user id. Emails, names, OCR text, storage paths, and full user ids are never shown.
