"""Tests for file upload validation."""

import io

import pytest
from fastapi import HTTPException, UploadFile

from backend.services.file_validation import validate_pdf, validate_xlsx


def _make_upload(filename: str, content: bytes, content_type: str) -> UploadFile:
    """Create an UploadFile with given filename, content, and content-type."""
    return UploadFile(
        file=io.BytesIO(content),
        filename=filename,
        headers={"content-type": content_type},
    )


class TestValidateXlsx:
    def test_valid_xlsx(self):
        f = _make_upload("data.xlsx", b"fake xlsx content", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        validate_xlsx(f)  # should not raise

    def test_valid_xls(self):
        f = _make_upload("data.xls", b"fake xls content", "application/vnd.ms-excel")
        validate_xlsx(f)

    def test_octet_stream_allowed(self):
        f = _make_upload("data.xlsx", b"content", "application/octet-stream")
        validate_xlsx(f)

    def test_rejects_csv_extension(self):
        f = _make_upload("data.csv", b"a,b,c", "text/csv")
        with pytest.raises(HTTPException) as exc_info:
            validate_xlsx(f)
        assert exc_info.value.status_code == 400
        assert ".csv" in str(exc_info.value.detail)

    def test_rejects_pdf_extension(self):
        f = _make_upload("doc.pdf", b"%PDF", "application/pdf")
        with pytest.raises(HTTPException) as exc_info:
            validate_xlsx(f)
        assert exc_info.value.status_code == 400

    def test_rejects_oversized(self):
        big_content = b"x" * (11 * 1024 * 1024)  # 11 MB
        f = _make_upload("big.xlsx", big_content, "application/octet-stream")
        with pytest.raises(HTTPException) as exc_info:
            validate_xlsx(f)
        assert exc_info.value.status_code == 400
        assert "Maximum: 10 MB" in str(exc_info.value.detail)

    def test_rejects_wrong_content_type(self):
        f = _make_upload("data.xlsx", b"content", "text/plain")
        with pytest.raises(HTTPException) as exc_info:
            validate_xlsx(f)
        assert exc_info.value.status_code == 400


class TestValidatePdf:
    def test_valid_pdf(self):
        f = _make_upload("invoice.pdf", b"%PDF-1.4 content", "application/pdf")
        validate_pdf(f)

    def test_rejects_docx_extension(self):
        f = _make_upload("doc.docx", b"fake docx", "application/octet-stream")
        with pytest.raises(HTTPException) as exc_info:
            validate_pdf(f)
        assert exc_info.value.status_code == 400
        assert ".docx" in str(exc_info.value.detail)

    def test_rejects_oversized(self):
        big_content = b"x" * (21 * 1024 * 1024)  # 21 MB
        f = _make_upload("big.pdf", big_content, "application/pdf")
        with pytest.raises(HTTPException) as exc_info:
            validate_pdf(f)
        assert exc_info.value.status_code == 400
        assert "Maximum: 20 MB" in str(exc_info.value.detail)

    def test_no_filename(self):
        f = _make_upload("", b"content", "application/pdf")
        with pytest.raises(HTTPException) as exc_info:
            validate_pdf(f)
        assert exc_info.value.status_code == 400
