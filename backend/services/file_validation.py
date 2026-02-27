"""File upload validation: type, extension, and size checks."""

from fastapi import HTTPException, UploadFile

XLSX_EXTENSIONS = {".xlsx", ".xls"}
PDF_EXTENSIONS = {".pdf"}
XLSX_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/octet-stream",
}
PDF_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}


def validate_upload(
    file: UploadFile,
    *,
    max_size_mb: int,
    allowed_extensions: set[str],
    allowed_content_types: set[str],
) -> None:
    """Validate an uploaded file.  Raises HTTPException(400) on failure."""
    # Check filename extension
    filename = (file.filename or "").lower()
    ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    if ext not in allowed_extensions:
        raise HTTPException(
            400,
            f"Ungültiger Dateityp '{ext}'. Erlaubt: {', '.join(sorted(allowed_extensions))}",
        )

    # Check content-type (lenient — also allow octet-stream)
    ct = (file.content_type or "").lower()
    if ct and ct != "application/octet-stream" and ct not in allowed_content_types:
        raise HTTPException(400, f"Ungültiger Content-Type '{ct}'.")

    # Check file size
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    max_bytes = max_size_mb * 1024 * 1024
    if size > max_bytes:
        raise HTTPException(
            400,
            f"Datei zu groß ({size / 1024 / 1024:.1f} MB). Maximum: {max_size_mb} MB.",
        )


def validate_xlsx(file: UploadFile, max_size_mb: int = 10) -> None:
    """Validate an XLSX upload (max 10 MB by default)."""
    validate_upload(
        file,
        max_size_mb=max_size_mb,
        allowed_extensions=XLSX_EXTENSIONS,
        allowed_content_types=XLSX_CONTENT_TYPES,
    )


def validate_pdf(file: UploadFile, max_size_mb: int = 20) -> None:
    """Validate a PDF upload (max 20 MB by default)."""
    validate_upload(
        file,
        max_size_mb=max_size_mb,
        allowed_extensions=PDF_EXTENSIONS,
        allowed_content_types=PDF_CONTENT_TYPES,
    )
