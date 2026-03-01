"""Tests for bulk PDF upload and confirmation endpoints."""

import io
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.config import settings
from backend.models.cost_category import CostCategory
from backend.models.provider_invoice import ProviderInvoice
from backend.services.pdf_extraction import ExtractedInvoiceData


@pytest.fixture
def sample_category(db_session):
    cat = CostCategory(
        id="aeologic",
        name="Aeologic",
        provider_name="Aeologic Technologies",
        currency="USD",
        billing_cycle="monthly",
        cost_type="direct",
        vat_status="reverse_charge",
        _bank_keywords='["aeologic", "aeo"]',
    )
    db_session.add(cat)
    db_session.commit()
    return cat


@pytest.fixture
def eur_category(db_session):
    cat = CostCategory(
        id="junior_fm",
        name="Junior FM",
        provider_name="Mikhail Iakovlev",
        currency="EUR",
        billing_cycle="monthly",
        cost_type="direct",
        vat_status="exempt",
        _bank_keywords='["iakovlev"]',
    )
    db_session.add(cat)
    db_session.commit()
    return cat


def _make_pdf_file(filename="test.pdf", content=b"%PDF-1.4 fake pdf content"):
    """Create a fake PDF UploadFile-like object for testing."""
    return (filename, io.BytesIO(content), "application/pdf")


@contextmanager
def _patch_settings(tmp_path):
    """Patch the settings singleton so CATEGORIES_DIR and DATA_DIR use tmp_path."""
    mock = MagicMock(spec=type(settings))
    mock.CATEGORIES_DIR = tmp_path / "categories"
    mock.DATA_DIR = tmp_path
    # Forward any other attribute to the real settings
    mock.IMPORTS_DIR = settings.IMPORTS_DIR
    mock.TEMPLATES_DIR = settings.TEMPLATES_DIR
    mock.GENERATED_DIR = settings.GENERATED_DIR
    with patch("backend.routers.provider_invoices.settings", mock):
        yield mock


class TestBulkUpload:
    """Tests for POST /api/provider-invoices/bulk-upload."""

    def test_bulk_upload_single_file(self, client, db_session, sample_category, tmp_path):
        """Upload a single PDF and get extraction results."""
        mock_extraction = ExtractedInvoiceData(
            filename="AEO000900.pdf",
            invoice_number="AEO000900",
            invoice_date=date(2025, 12, 1),
            amount=1500.00,
            currency="USD",
            category_id="aeologic",
            confidence="high",
            raw_text="Invoice # AEO000900 Total Due $1,500.00",
        )

        (tmp_path / "categories" / "aeologic").mkdir(parents=True)

        with patch("backend.services.pdf_extraction.extract_invoice_data", return_value=mock_extraction), \
             _patch_settings(tmp_path):
            resp = client.post(
                "/api/provider-invoices/bulk-upload",
                files=[("files", _make_pdf_file("AEO000900.pdf"))],
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["extracted"] == 1
        assert len(data["extractions"]) == 1
        ext = data["extractions"][0]
        assert ext["invoice_number"] == "AEO000900"
        assert ext["amount"] == 1500.00
        assert ext["currency"] == "USD"
        assert ext["category_id"] == "aeologic"
        assert ext["confidence"] == "high"

    def test_bulk_upload_multiple_files(self, client, db_session, sample_category, eur_category, tmp_path):
        """Upload multiple PDFs."""
        extractions = [
            ExtractedInvoiceData(
                filename="AEO000900.pdf",
                invoice_number="AEO000900",
                invoice_date=date(2025, 12, 1),
                amount=1500.00,
                currency="USD",
                category_id="aeologic",
                confidence="high",
            ),
            ExtractedInvoiceData(
                filename="ER2512-21.pdf",
                invoice_number="12/2025",
                invoice_date=date(2025, 12, 21),
                amount=1600.00,
                currency="EUR",
                category_id="junior_fm",
                confidence="high",
            ),
        ]
        call_count = 0

        def mock_extract(*args, **kwargs):
            nonlocal call_count
            result = extractions[call_count]
            call_count += 1
            return result

        (tmp_path / "categories" / "aeologic").mkdir(parents=True)
        (tmp_path / "categories" / "junior_fm").mkdir(parents=True)

        with patch("backend.services.pdf_extraction.extract_invoice_data", side_effect=mock_extract), \
             _patch_settings(tmp_path):
            resp = client.post(
                "/api/provider-invoices/bulk-upload",
                files=[
                    ("files", _make_pdf_file("AEO000900.pdf")),
                    ("files", _make_pdf_file("ER2512-21.pdf")),
                ],
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["extracted"] == 2

    def test_bulk_upload_with_preset_category(self, client, db_session, sample_category, tmp_path):
        """Upload with preset category_id skips category detection."""
        mock_extraction = ExtractedInvoiceData(
            filename="test.pdf",
            invoice_number="AEO000999",
            category_id="aeologic",
            confidence="medium",
        )

        (tmp_path / "categories" / "aeologic").mkdir(parents=True)

        with patch("backend.services.pdf_extraction.extract_invoice_data", return_value=mock_extraction) as mock_fn, \
             _patch_settings(tmp_path):
            resp = client.post(
                "/api/provider-invoices/bulk-upload?category_id=aeologic",
                files=[("files", _make_pdf_file("test.pdf"))],
            )

        assert resp.status_code == 200
        # Verify preset_category_id was passed to extract_invoice_data
        mock_fn.assert_called_once()
        _, kwargs = mock_fn.call_args
        assert kwargs.get("preset_category_id") == "aeologic"

    def test_bulk_upload_no_extraction(self, client, db_session, sample_category, tmp_path):
        """Upload a PDF that yields no extracted data (e.g., scanned)."""
        mock_extraction = ExtractedInvoiceData(
            filename="scanned.pdf",
            confidence="low",
        )

        (tmp_path / "categories" / "inbox").mkdir(parents=True)

        with patch("backend.services.pdf_extraction.extract_invoice_data", return_value=mock_extraction), \
             _patch_settings(tmp_path):
            resp = client.post(
                "/api/provider-invoices/bulk-upload",
                files=[("files", _make_pdf_file("scanned.pdf"))],
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["extracted"] == 0
        ext = data["extractions"][0]
        assert ext["invoice_number"] is None
        assert ext["confidence"] == "low"

    def test_bulk_upload_rejects_non_pdf(self, client, db_session):
        """Non-PDF files should be rejected."""
        resp = client.post(
            "/api/provider-invoices/bulk-upload",
            files=[("files", ("test.xlsx", io.BytesIO(b"not a pdf"), "application/vnd.ms-excel"))],
        )
        assert resp.status_code == 400


class TestBulkConfirm:
    """Tests for POST /api/provider-invoices/bulk-confirm."""

    def test_bulk_confirm_creates_records(self, client, db_session, sample_category, tmp_path):
        """Confirming creates provider invoice records."""
        cat_dir = tmp_path / "categories" / "aeologic"
        cat_dir.mkdir(parents=True)
        (cat_dir / "AEO000900.pdf").write_bytes(b"%PDF-1.4 fake")

        with _patch_settings(tmp_path):
            resp = client.post(
                "/api/provider-invoices/bulk-confirm",
                json={
                    "items": [
                        {
                            "filename": "AEO000900.pdf",
                            "stored_path": "categories/aeologic/AEO000900.pdf",
                            "invoice_number": "AEO000900",
                            "invoice_date": "2025-12-01",
                            "amount": 1500.00,
                            "currency": "USD",
                            "category_id": "aeologic",
                        }
                    ]
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 1
        assert data["errors"] == []

        # Verify record in DB
        inv = db_session.query(ProviderInvoice).filter_by(invoice_number="AEO000900").first()
        assert inv is not None
        assert inv.amount == 1500.00
        assert inv.currency == "USD"
        assert inv.category_id == "aeologic"
        assert inv.assigned_month == "2025-12"

    def test_bulk_confirm_multiple_items(self, client, db_session, sample_category, eur_category, tmp_path):
        """Confirming multiple items."""
        for cat in ["aeologic", "junior_fm"]:
            d = tmp_path / "categories" / cat
            d.mkdir(parents=True)
            (d / f"test_{cat}.pdf").write_bytes(b"%PDF-1.4 fake")

        with _patch_settings(tmp_path):
            resp = client.post(
                "/api/provider-invoices/bulk-confirm",
                json={
                    "items": [
                        {
                            "filename": "test_aeologic.pdf",
                            "stored_path": "categories/aeologic/test_aeologic.pdf",
                            "invoice_number": "AEO000900",
                            "invoice_date": "2025-12-01",
                            "amount": 1500.00,
                            "currency": "USD",
                            "category_id": "aeologic",
                        },
                        {
                            "filename": "test_junior_fm.pdf",
                            "stored_path": "categories/junior_fm/test_junior_fm.pdf",
                            "invoice_number": "12/2025",
                            "invoice_date": "2025-12-21",
                            "amount": 1600.00,
                            "currency": "EUR",
                            "category_id": "junior_fm",
                        },
                    ]
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 2

    def test_bulk_confirm_with_assigned_month(self, client, db_session, sample_category, tmp_path):
        """Custom assigned_month is respected."""
        cat_dir = tmp_path / "categories" / "aeologic"
        cat_dir.mkdir(parents=True)
        (cat_dir / "test.pdf").write_bytes(b"%PDF-1.4 fake")

        with _patch_settings(tmp_path):
            resp = client.post(
                "/api/provider-invoices/bulk-confirm",
                json={
                    "items": [
                        {
                            "filename": "test.pdf",
                            "stored_path": "categories/aeologic/test.pdf",
                            "invoice_number": "AEO000900",
                            "invoice_date": "2025-12-01",
                            "amount": 1500.00,
                            "currency": "USD",
                            "category_id": "aeologic",
                            "assigned_month": "2025-11",
                        }
                    ]
                },
            )

        assert resp.status_code == 200
        inv = db_session.query(ProviderInvoice).filter_by(invoice_number="AEO000900").first()
        assert inv.assigned_month == "2025-11"

    def test_bulk_confirm_moves_from_inbox(self, client, db_session, sample_category, tmp_path):
        """Files in inbox/ get moved to the correct category dir on confirm."""
        inbox_dir = tmp_path / "categories" / "inbox"
        inbox_dir.mkdir(parents=True)
        (inbox_dir / "AEO000900.pdf").write_bytes(b"%PDF-1.4 fake")
        (tmp_path / "categories" / "aeologic").mkdir(parents=True)

        with _patch_settings(tmp_path):
            resp = client.post(
                "/api/provider-invoices/bulk-confirm",
                json={
                    "items": [
                        {
                            "filename": "AEO000900.pdf",
                            "stored_path": "categories/inbox/AEO000900.pdf",
                            "invoice_number": "AEO000900",
                            "invoice_date": "2025-12-01",
                            "amount": 1500.00,
                            "currency": "USD",
                            "category_id": "aeologic",
                        }
                    ]
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 1

        inv = db_session.query(ProviderInvoice).filter_by(invoice_number="AEO000900").first()
        assert "aeologic" in inv.file_path
        assert "inbox" not in inv.file_path


class TestPdfExtraction:
    """Unit tests for the PDF extraction service."""

    def test_extract_aeologic_patterns(self):
        from backend.services.pdf_extraction import _extract_aeologic

        text = """
        Invoice #: AEO000852
        Date: 30/12/2025
        Total Due: $1,302.00
        """
        result = _extract_aeologic(text)
        assert result["invoice_number"] == "AEO000852"
        assert result["invoice_date"] == date(2025, 12, 30)
        assert result["amount"] == 1302.00
        assert result["currency"] == "USD"

    def test_extract_aeologic_month_date(self):
        from backend.services.pdf_extraction import _extract_aeologic

        text = """
        Invoice # AEO000900
        December 1, 2025
        Amount Due: $1,500.00
        """
        result = _extract_aeologic(text)
        assert result["invoice_number"] == "AEO000900"
        assert result["invoice_date"] == date(2025, 12, 1)
        assert result["amount"] == 1500.00

    def test_extract_junior_fm_patterns(self):
        from backend.services.pdf_extraction import _extract_junior_fm

        text = """
        Rechnung 12/2025
        Datum: 21.12.2025
        Summe: 1.600,00 EUR
        """
        result = _extract_junior_fm(text)
        assert result["invoice_number"] == "12/2025"
        assert result["invoice_date"] == date(2025, 12, 21)
        assert result["amount"] == 1600.00
        assert result["currency"] == "EUR"

    def test_extract_kaletsch_patterns(self):
        from backend.services.pdf_extraction import _extract_kaletsch

        text = """
        Invoice INV320
        Date: 01/10/2025
        Total: €4,500.00
        """
        result = _extract_kaletsch(text)
        assert result["invoice_number"] == "INV320"
        assert result["invoice_date"] == date(2025, 10, 1)
        assert result["amount"] == 4500.00
        assert result["currency"] == "EUR"

    def test_extract_kaletsch_german_format(self):
        from backend.services.pdf_extraction import _extract_kaletsch

        text = """
        Invoice INV307
        Date: 15.01.2025
        Total: EUR 4.500,00
        """
        result = _extract_kaletsch(text)
        assert result["invoice_number"] == "INV307"
        assert result["invoice_date"] == date(2025, 1, 15)
        assert result["amount"] == 4500.00

    def test_extract_invoice_data_no_text(self, tmp_path):
        """Graceful fallback when pdfplumber can't extract text."""
        from backend.services.pdf_extraction import extract_invoice_data

        # Create a minimal fake PDF file
        pdf_file = tmp_path / "empty.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake content")

        result = extract_invoice_data(
            pdf_path=str(pdf_file),
            filename="empty.pdf",
            categories=[],
        )
        assert result.filename == "empty.pdf"
        assert result.confidence == "low"
        assert result.invoice_number is None

    def test_category_matching_from_text(self):
        from backend.services.pdf_extraction import _match_category_from_text

        class MockCategory:
            def __init__(self, cid, keywords):
                self.id = cid
                self.bank_keywords = keywords

        cats = [
            MockCategory("aeologic", ["aeologic", "aeo"]),
            MockCategory("junior_fm", ["iakovlev"]),
        ]
        assert _match_category_from_text("Invoice from Aeologic Technologies", cats) == "aeologic"
        assert _match_category_from_text("Rechnung Iakovlev", cats) == "junior_fm"
        assert _match_category_from_text("Unknown vendor", cats) is None
