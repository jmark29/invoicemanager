"""Tests for Phase 3B — CRUD API endpoints."""

from datetime import date

import pytest
from fastapi.testclient import TestClient


# ─── Client CRUD ────────────────────────────────────────────────


class TestClientAPI:
    def test_create_client(self, client: TestClient):
        resp = client.post("/api/clients", json={
            "id": "drs",
            "client_number": "02",
            "name": "DRS Holding AG",
            "address_line1": "Am Sandtorkai 58",
            "zip_city": "20457 Hamburg",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "drs"
        assert data["name"] == "DRS Holding AG"
        assert data["vat_rate"] == 0.19

    def test_create_duplicate_client(self, client: TestClient):
        client.post("/api/clients", json={
            "id": "drs", "client_number": "02", "name": "DRS",
            "address_line1": "x", "zip_city": "y",
        })
        resp = client.post("/api/clients", json={
            "id": "drs", "client_number": "02", "name": "DRS",
            "address_line1": "x", "zip_city": "y",
        })
        assert resp.status_code == 409

    def test_list_clients(self, client: TestClient):
        client.post("/api/clients", json={
            "id": "c1", "client_number": "01", "name": "Client 1",
            "address_line1": "x", "zip_city": "y",
        })
        resp = client.get("/api/clients")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_client(self, client: TestClient):
        client.post("/api/clients", json={
            "id": "c2", "client_number": "02", "name": "Client 2",
            "address_line1": "x", "zip_city": "y",
        })
        resp = client.get("/api/clients/c2")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Client 2"

    def test_get_client_not_found(self, client: TestClient):
        resp = client.get("/api/clients/nonexistent")
        assert resp.status_code == 404

    def test_update_client(self, client: TestClient):
        client.post("/api/clients", json={
            "id": "c3", "client_number": "03", "name": "Old Name",
            "address_line1": "x", "zip_city": "y",
        })
        resp = client.patch("/api/clients/c3", json={"name": "New Name"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_list_active_only(self, client: TestClient):
        client.post("/api/clients", json={
            "id": "active", "client_number": "01", "name": "Active",
            "address_line1": "x", "zip_city": "y", "active": True,
        })
        client.post("/api/clients", json={
            "id": "inactive", "client_number": "02", "name": "Inactive",
            "address_line1": "x", "zip_city": "y", "active": False,
        })
        resp = client.get("/api/clients?active_only=true")
        names = [c["name"] for c in resp.json()]
        assert "Active" in names
        assert "Inactive" not in names


# ─── Cost Category CRUD ─────────────────────────────────────────


class TestCostCategoryAPI:
    def test_create_category(self, client: TestClient):
        resp = client.post("/api/cost-categories", json={
            "id": "junior_fm",
            "name": "Junior FM",
            "provider_name": "Mikhail Iakovlev",
            "billing_cycle": "monthly",
            "cost_type": "direct",
            "bank_keywords": ["iakovlev", "mikhail"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "junior_fm"
        assert data["bank_keywords"] == ["iakovlev", "mikhail"]

    def test_update_category_keywords(self, client: TestClient):
        client.post("/api/cost-categories", json={
            "id": "cat1", "name": "Cat", "billing_cycle": "monthly",
            "cost_type": "direct", "bank_keywords": ["old"],
        })
        resp = client.patch("/api/cost-categories/cat1", json={
            "bank_keywords": ["new1", "new2"],
        })
        assert resp.status_code == 200
        assert resp.json()["bank_keywords"] == ["new1", "new2"]

    def test_list_categories(self, client: TestClient):
        client.post("/api/cost-categories", json={
            "id": "cat2", "name": "Cat 2", "billing_cycle": "quarterly",
            "cost_type": "distributed",
        })
        resp = client.get("/api/cost-categories")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


# ─── Line Item Definition CRUD ──────────────────────────────────


class TestLineItemDefinitionAPI:
    def _setup_client(self, client: TestClient):
        client.post("/api/clients", json={
            "id": "drs", "client_number": "02", "name": "DRS",
            "address_line1": "x", "zip_city": "y",
        })

    def test_create_definition(self, client: TestClient):
        self._setup_client(client)
        resp = client.post("/api/line-item-definitions", json={
            "client_id": "drs",
            "position": 1,
            "label": "Team & PM",
            "source_type": "fixed",
            "fixed_amount": 16450.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["position"] == 1
        assert data["fixed_amount"] == 16450.0

    def test_list_by_client(self, client: TestClient):
        self._setup_client(client)
        client.post("/api/line-item-definitions", json={
            "client_id": "drs", "position": 1, "label": "PM",
            "source_type": "fixed", "fixed_amount": 100.0,
        })
        resp = client.get("/api/line-item-definitions?client_id=drs")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_delete_definition(self, client: TestClient):
        self._setup_client(client)
        create = client.post("/api/line-item-definitions", json={
            "client_id": "drs", "position": 99, "label": "To Delete",
            "source_type": "manual",
        })
        did = create.json()["id"]
        resp = client.delete(f"/api/line-item-definitions/{did}")
        assert resp.status_code == 204

        resp = client.get(f"/api/line-item-definitions/{did}")
        assert resp.status_code == 404


# ─── Provider Invoice CRUD ───────────────────────────────────────


class TestProviderInvoiceAPI:
    def _setup(self, client: TestClient):
        client.post("/api/cost-categories", json={
            "id": "junior_fm", "name": "Junior FM",
            "billing_cycle": "monthly", "cost_type": "direct",
        })

    def test_create_provider_invoice(self, client: TestClient):
        self._setup(client)
        resp = client.post("/api/provider-invoices", json={
            "category_id": "junior_fm",
            "invoice_number": "01/2025",
            "invoice_date": "2025-01-15",
            "amount": 1300.0,
            "assigned_month": "2025-01",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["amount"] == 1300.0
        assert data["assigned_month"] == "2025-01"

    def test_create_with_covers_months(self, client: TestClient):
        client.post("/api/cost-categories", json={
            "id": "kaletsch", "name": "Cloud Engineer",
            "billing_cycle": "quarterly", "cost_type": "distributed",
        })
        resp = client.post("/api/provider-invoices", json={
            "category_id": "kaletsch",
            "invoice_number": "INV307",
            "invoice_date": "2025-03-01",
            "amount": 8280.0,
            "covers_months": ["2025-01", "2025-02", "2025-03"],
        })
        assert resp.status_code == 201
        assert resp.json()["covers_months"] == ["2025-01", "2025-02", "2025-03"]

    def test_list_by_category(self, client: TestClient):
        self._setup(client)
        client.post("/api/provider-invoices", json={
            "category_id": "junior_fm",
            "invoice_number": "02/2025",
            "invoice_date": "2025-02-15",
            "amount": 3800.0,
            "assigned_month": "2025-02",
        })
        resp = client.get("/api/provider-invoices?category_id=junior_fm")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_update_provider_invoice(self, client: TestClient):
        self._setup(client)
        create = client.post("/api/provider-invoices", json={
            "category_id": "junior_fm",
            "invoice_number": "test",
            "invoice_date": "2025-01-15",
            "amount": 100.0,
        })
        inv_id = create.json()["id"]
        resp = client.patch(f"/api/provider-invoices/{inv_id}", json={
            "amount": 200.0,
            "assigned_month": "2025-02",
        })
        assert resp.status_code == 200
        assert resp.json()["amount"] == 200.0
        assert resp.json()["assigned_month"] == "2025-02"

    def test_delete_provider_invoice(self, client: TestClient):
        self._setup(client)
        create = client.post("/api/provider-invoices", json={
            "category_id": "junior_fm",
            "invoice_number": "del",
            "invoice_date": "2025-01-01",
            "amount": 50.0,
        })
        inv_id = create.json()["id"]
        resp = client.delete(f"/api/provider-invoices/{inv_id}")
        assert resp.status_code == 204


# ─── Bank Transaction CRUD ──────────────────────────────────────


class TestBankTransactionAPI:
    def test_create_bank_transaction(self, client: TestClient):
        resp = client.post("/api/bank-transactions", json={
            "booking_date": "2025-01-06",
            "description": "KALETSCH COMPANY INV307",
            "amount_eur": -8295.0,
        })
        assert resp.status_code == 201
        assert resp.json()["amount_eur"] == -8295.0

    def test_update_bank_transaction(self, client: TestClient):
        create = client.post("/api/bank-transactions", json={
            "booking_date": "2025-01-06",
            "description": "Some payment",
            "amount_eur": -100.0,
        })
        tx_id = create.json()["id"]
        resp = client.patch(f"/api/bank-transactions/{tx_id}", json={
            "notes": "Matched manually",
        })
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Matched manually"


# ─── Payment Receipt CRUD ───────────────────────────────────────


class TestPaymentReceiptAPI:
    def _setup_client(self, client: TestClient):
        client.post("/api/clients", json={
            "id": "drs", "client_number": "02", "name": "DRS",
            "address_line1": "x", "zip_city": "y",
        })

    def test_create_payment(self, client: TestClient):
        self._setup_client(client)
        resp = client.post("/api/payments", json={
            "client_id": "drs",
            "payment_date": "2025-03-15",
            "amount_eur": 42287.60,
            "reference": "Jan 2025 invoice",
        })
        assert resp.status_code == 201
        assert resp.json()["amount_eur"] == 42287.60

    def test_list_payments(self, client: TestClient):
        self._setup_client(client)
        client.post("/api/payments", json={
            "client_id": "drs", "payment_date": "2025-03-15",
            "amount_eur": 100.0,
        })
        resp = client.get("/api/payments?client_id=drs")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_delete_payment(self, client: TestClient):
        self._setup_client(client)
        create = client.post("/api/payments", json={
            "client_id": "drs", "payment_date": "2025-03-15",
            "amount_eur": 50.0,
        })
        pid = create.json()["id"]
        resp = client.delete(f"/api/payments/{pid}")
        assert resp.status_code == 204


# ─── Working Days API ────────────────────────────────────────────


class TestWorkingDaysAPI:
    def test_get_working_days(self, client: TestClient):
        resp = client.get("/api/working-days/2025/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["year"] == 2025
        assert data["month"] == 1
        assert data["working_days"] == 22

    def test_working_days_with_holidays(self, client: TestClient):
        resp = client.get("/api/working-days/2025/4")
        data = resp.json()
        assert data["working_days"] == 20
        # April has Karfreitag and Ostermontag
        assert len(data["holidays"]) >= 2

    def test_invalid_month(self, client: TestClient):
        resp = client.get("/api/working-days/2025/13")
        assert resp.status_code == 400


# ─── Generated Invoice API (read-only for now) ──────────────────


class TestGeneratedInvoiceAPI:
    def test_list_empty(self, client: TestClient):
        resp = client.get("/api/invoices")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_not_found(self, client: TestClient):
        resp = client.get("/api/invoices/999")
        assert resp.status_code == 404
