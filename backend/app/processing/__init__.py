"""Image loading, quality checks, OCR, and ID masking.

These functions work on bytes and pictures. They do not talk to Supabase.
"""

from app.processing.pipeline import process_document

__all__ = ["process_document"]
