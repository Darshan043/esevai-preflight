"""Default thresholds used only when a document's rules omit that key.

A service can set a stricter or looser number in required_documents.rules.
These defaults are not official government rules.
"""

# A photo softer than this fails the sharpness check.
DEFAULT_MIN_BLUR = 100.0
# A page smaller than this is a warning, not a failure.
DEFAULT_MIN_WIDTH = 800
DEFAULT_MIN_HEIGHT = 600
# Brightness outside this range is a warning.
DEFAULT_MIN_BRIGHTNESS = 40.0
DEFAULT_MAX_BRIGHTNESS = 220.0
# OCR confidence below this is a warning. Blank pages fail separately.
DEFAULT_MIN_OCR_CONFIDENCE = 40.0
# Tilt above this many degrees is a warning.
DEFAULT_MAX_SKEW = 15.0
# Fewer words than this, together with low confidence, means the page is hard to read.
DEFAULT_MIN_WORDS = 8
# Fuzzy keyword match. 100 is an exact match.
KEYWORD_MATCH = 85
# Name comparison. 85 and above passes. 70 to 84 warns. Below 70 fails.
NAME_MATCH_PASS = 85
NAME_MATCH_WARN = 70
