"""Server-side file-upload guards.

Every FileField in this app previously had no validation at all beyond
the frontend's `accept="application/pdf"` attribute — which is cosmetic
only, since it does nothing to stop a direct API call. Any authenticated
member with upload rights could attach a file of any type or size (an
executable, a multi-gigabyte file for a storage-exhaustion DoS, or an
.html file that a browser would happily render if it were ever served
inline). These close that gap.

Two named, module-level functions rather than a factory returning a
closure per limit: Django's migration writer needs to serialize
validators by dotted import path, which only works for a real
module-level callable, not a closure — `validate_document_size` and
`validate_video_size` are each importable at a stable path.
"""

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

# Documents, evidence, and supplier agreements: office documents, PDFs,
# spreadsheets, and images — the kinds of things actually meant to be
# attached as a controlled document or compliance evidence, not an
# arbitrary executable or script.
DOCUMENT_EXTENSIONS = ['pdf', 'doc', 'docx', 'odt', 'txt', 'csv', 'xls', 'xlsx', 'png', 'jpg', 'jpeg']
validate_document_extension = FileExtensionValidator(allowed_extensions=DOCUMENT_EXTENSIONS)

# Training videos are real video files, an order of magnitude bigger
# than any document.
VIDEO_EXTENSIONS = ['mp4', 'mov', 'webm', 'm4v']
validate_video_extension = FileExtensionValidator(allowed_extensions=VIDEO_EXTENSIONS)


def validate_document_size(value):
    max_bytes = 25 * 1024 * 1024
    if value.size > max_bytes:
        raise ValidationError(f'File is too large ({value.size / (1024 * 1024):.1f} MB) — the limit is 25 MB.')


def validate_video_size(value):
    max_bytes = 500 * 1024 * 1024
    if value.size > max_bytes:
        raise ValidationError(f'File is too large ({value.size / (1024 * 1024):.1f} MB) — the limit is 500 MB.')
