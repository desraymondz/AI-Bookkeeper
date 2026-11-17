"""Invoice file storage. See planning/03-tech-stack.md section 9 and planning/01-prd.md#f-011."""

from bookkeeper.storage.files import (
    MAX_BYTES,
    StoredDocument,
    detect_type,
    resolve_path,
    slugify,
    store_document,
)

__all__ = [
    "MAX_BYTES",
    "StoredDocument",
    "detect_type",
    "resolve_path",
    "slugify",
    "store_document",
]
