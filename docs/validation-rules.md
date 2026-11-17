# Validation rule keys

Each required document row can set these values. A missing key uses the default in `backend/app/validation/defaults.py`, or the check is skipped when the key is what turns the check on.

These are application settings, not official government rules.

## min_width

Smallest width in pixels. Below this is a warning.

Example: `800`

## min_height

Smallest height in pixels. Below this is a warning.

Example: `600`

## min_blur_score

Lowest Laplacian sharpness. Below this fails.

Example: `100`

## min_brightness

Lowest average brightness, from 0 to 255. Below this is a warning.

Example: `60`

## max_brightness

Highest average brightness. Above this is a warning.

Example: `220`

## id_number_pattern

Turns on the ID checksum check. Any non-empty value enables it. The result keeps only the last 4 digits.

Example: `"aadhaar"`

## max_age_days

Maximum age of the newest date found on the page, in days. Older than this fails. `validity_days` is used as well, and the smaller of the two applies.

Example: `180`

## check_name_match

When true, the guessed name is compared with other documents that also set this flag.

Example: `true`

## keywords

Words that show the file is the right kind of document. At least one must match, including a close spelling. English and Tamil lists are both used.

Example: `{"en": ["address proof"], "ta": ["முகவரி"]}`

## required_fields

Which details to look for. Supported values are `name`, `date`, and `number`. A missing one is a warning.

Example: `["name", "date"]`

## validity_days

Same age check as `max_age_days`, stored on the document row instead of inside `rules`.

Example: `365`
