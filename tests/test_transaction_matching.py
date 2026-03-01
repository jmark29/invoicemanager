"""Tests for the transaction matching service and API endpoints."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend.models.bank_transaction import BankTransaction
from backend.models.cost_category import CostCategory
from backend.models.provider_invoice import ProviderInvoice
from backend.services.transaction_matching import (
    apply_match,
    auto_match_after_bank_import,
    auto_match_after_invoice_creation,
    find_invoice_matches_for_transaction,
    find_transaction_matches_for_invoice,
    reject_match,
)


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


@pytest.fixture
def sample_invoice(db_session, sample_category):
    inv = ProviderInvoice(
        category_id="aeologic",
        invoice_number="AEO000852",
        invoice_date=date(2025, 12, 30),
        amount=1302.00,
        currency="USD",
        assigned_month="2025-12",
    )
    db_session.add(inv)
    db_session.commit()
    return inv


@pytest.fixture
def eur_invoice(db_session, eur_category):
    inv = ProviderInvoice(
        category_id="junior_fm",
        invoice_number="12/2025",
        invoice_date=date(2025, 12, 21),
        amount=1600.00,
        currency="EUR",
        assigned_month="2025-12",
    )
    db_session.add(inv)
    db_session.commit()
    return inv


@pytest.fixture
def sample_transaction(db_session, sample_category):
    tx = BankTransaction(
        booking_date=date(2025, 12, 30),
        description="INVOICE AEO000852 AEOLOGIC TECHNOLOGIES",
        amount_eur=-1276.43,
        category_id="aeologic",
    )
    db_session.add(tx)
    db_session.commit()
    return tx


@pytest.fixture
def eur_transaction(db_session, eur_category):
    tx = BankTransaction(
        booking_date=date(2025, 12, 22),
        description="IAKOVLEV RE. NR.: 12/2025",
        amount_eur=-1600.00,
        category_id="junior_fm",
    )
    db_session.add(tx)
    db_session.commit()
    return tx


class TestMatchFinding:
    """Tests for finding match candidates."""

    def test_match_by_invoice_number_high_confidence(self, db_session, sample_invoice, sample_transaction):
        candidates = find_invoice_matches_for_transaction(sample_transaction, db_session)
        assert len(candidates) >= 1
        best = candidates[0]
        assert best.confidence >= 0.95
        assert best.match_reason == "invoice_number"
        assert best.provider_invoice_id == sample_invoice.id

    def test_match_by_invoice_number_eur(self, db_session, eur_invoice, eur_transaction):
        candidates = find_invoice_matches_for_transaction(eur_transaction, db_session)
        assert len(candidates) >= 1
        best = candidates[0]
        assert best.confidence >= 0.95
        assert best.match_reason == "invoice_number"

    def test_no_match_different_category(self, db_session, sample_category, sample_invoice):
        """Transaction in a different category shouldn't match."""
        other_cat = CostCategory(
            id="other", name="Other", currency="EUR",
            billing_cycle="monthly", cost_type="direct", vat_status="standard",
        )
        db_session.add(other_cat)
        tx = BankTransaction(
            booking_date=date(2025, 12, 30),
            description="SOME OTHER PAYMENT",
            amount_eur=-1302.00,
            category_id="other",
        )
        db_session.add(tx)
        db_session.commit()
        candidates = find_invoice_matches_for_transaction(tx, db_session)
        assert all(c.match_reason != "invoice_number" for c in candidates)

    def test_already_linked_skipped(self, db_session, sample_category, sample_invoice):
        tx = BankTransaction(
            booking_date=date(2025, 12, 30),
            description="INVOICE AEO000852",
            amount_eur=-1276.43,
            category_id="aeologic",
            provider_invoice_id=sample_invoice.id,
        )
        db_session.add(tx)
        db_session.commit()
        candidates = find_invoice_matches_for_transaction(tx, db_session)
        assert len(candidates) == 0  # Already linked, skip

    def test_reverse_match_invoice_to_transaction(self, db_session, sample_invoice, sample_transaction):
        candidates = find_transaction_matches_for_invoice(sample_invoice, db_session)
        assert len(candidates) >= 1
        best = candidates[0]
        assert best.confidence >= 0.95
        assert best.bank_transaction_id == sample_transaction.id

    def test_amount_date_medium_confidence(self, db_session, eur_category, eur_invoice):
        """EUR invoice with matching amount + close date = medium confidence."""
        tx = BankTransaction(
            booking_date=date(2025, 12, 23),
            description="ÜBERWEISUNG IAKOVLEV",
            amount_eur=-1600.00,
            category_id="junior_fm",
        )
        db_session.add(tx)
        db_session.commit()
        candidates = find_transaction_matches_for_invoice(eur_invoice, db_session)
        # Should find a match (might be invoice_number or amount_date)
        assert len(candidates) >= 1


class TestApplyMatch:
    """Tests for applying matches and computing FX values."""

    def test_apply_match_eur(self, db_session, eur_invoice, eur_transaction):
        result = apply_match(eur_transaction.id, eur_invoice.id, db_session)
        assert result["fx_rate"] == 1.0
        assert result["amount_eur"] == 1600.00
        assert result["bank_fee"] == 0.0

        db_session.refresh(eur_invoice)
        assert eur_invoice.payment_status == "matched"
        assert eur_invoice.matched_transaction_id == eur_transaction.id
        assert eur_invoice.amount_eur == 1600.00

        db_session.refresh(eur_transaction)
        assert eur_transaction.provider_invoice_id == eur_invoice.id
        assert eur_transaction.match_status == "auto_matched"

    def test_apply_match_usd(self, db_session, sample_invoice, sample_transaction):
        result = apply_match(sample_transaction.id, sample_invoice.id, db_session)
        assert result["amount_eur"] == 1276.43
        assert result["fx_rate"] == pytest.approx(1276.43 / 1302.00, rel=1e-4)
        assert result["bank_fee"] is None  # Unknown for USD

        db_session.refresh(sample_invoice)
        assert sample_invoice.payment_status == "matched"
        assert sample_invoice.amount_eur == 1276.43

    def test_apply_match_with_bank_fee_override(self, db_session, eur_category, eur_invoice):
        tx = BankTransaction(
            booking_date=date(2025, 12, 22),
            description="IAKOVLEV",
            amount_eur=-1605.00,
            category_id="junior_fm",
        )
        db_session.add(tx)
        db_session.commit()
        result = apply_match(tx.id, eur_invoice.id, db_session, bank_fee_override=5.00)
        assert result["bank_fee"] == 5.00
        assert result["amount_eur"] == 1605.00

    def test_reject_match(self, db_session, sample_transaction):
        sample_transaction.match_status = "suggested"
        db_session.commit()
        reject_match(sample_transaction.id, db_session)
        db_session.refresh(sample_transaction)
        assert sample_transaction.match_status == "rejected"


class TestAutoMatch:
    """Tests for auto-matching after imports and invoice creation."""

    def test_auto_match_after_bank_import(self, db_session, sample_invoice, sample_transaction):
        stats = auto_match_after_bank_import([sample_transaction.id], db_session)
        assert stats.auto_matched == 1
        db_session.refresh(sample_invoice)
        assert sample_invoice.payment_status == "matched"

    def test_auto_match_after_invoice_creation(self, db_session, sample_category, sample_transaction):
        inv = ProviderInvoice(
            category_id="aeologic",
            invoice_number="AEO000852",
            invoice_date=date(2025, 12, 30),
            amount=1302.00,
            currency="USD",
        )
        db_session.add(inv)
        db_session.commit()
        result = auto_match_after_invoice_creation(inv.id, db_session)
        assert result is not None
        assert result.confidence >= 0.95
        db_session.refresh(inv)
        assert inv.payment_status == "matched"


class TestMatchEndpoints:
    """Tests for the match and manual-match API endpoints."""

    def test_manual_match_endpoint(self, client, db_session, sample_invoice, sample_transaction):
        resp = client.post(
            f"/api/bank-transactions/{sample_transaction.id}/manual-match",
            json={"provider_invoice_id": sample_invoice.id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["amount_eur"] == 1276.43

    def test_manual_match_not_found(self, client, db_session):
        resp = client.post(
            "/api/bank-transactions/9999/manual-match",
            json={"provider_invoice_id": 1},
        )
        assert resp.status_code == 404

    def test_confirm_match_reject(self, client, db_session, sample_transaction):
        sample_transaction.match_status = "suggested"
        db_session.commit()
        resp = client.post(
            f"/api/bank-transactions/{sample_transaction.id}/match",
            json={"action": "reject"},
        )
        assert resp.status_code == 200
        assert resp.json()["match_status"] == "rejected"
