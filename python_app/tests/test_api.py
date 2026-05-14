"""Integration tests covering the full FastAPI surface.

Exercises the customer -> account -> deposit -> withdraw -> transfer ->
delete flow end-to-end, plus the meta endpoints.
"""

from __future__ import annotations

import datetime as _dt

import pytest


def _make_customer_payload(name="Jane Doe"):
    return {
        "name": name,
        "address": "1 Demo Lane, Hursley, Winchester",
        "date_of_birth": _dt.date(1990, 5, 10).isoformat(),
        "credit_score": 720,
    }


def test_health_endpoint(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_meta_endpoints(client):
    assert client.get("/meta/sortcode").json() == {"sort_code": "987654"}
    assert (
        client.get("/meta/company").json()["company_name"]
        == "CICS Bank Sample Application"
    )


def test_full_customer_account_lifecycle(client):
    # 1. Create customer
    r = client.post("/customers", json=_make_customer_payload())
    assert r.status_code == 201, r.text
    cust = r.json()
    cust_number = cust["number"]

    # 2. Create an account for that customer
    r = client.post(
        "/accounts",
        json={
            "customer_number": cust_number,
            "type": "CURRENT",
            "interest_rate": "1.50",
            "overdraft_limit": 200,
        },
    )
    assert r.status_code == 201, r.text
    account = r.json()
    acc_number = account["number"]

    # 3. Get account & list customer's accounts
    assert client.get(f"/accounts/{acc_number}").status_code == 200
    listing = client.get(f"/customers/{cust_number}/accounts").json()
    assert any(a["number"] == acc_number for a in listing)

    # 4. Deposit (teller credit) then withdraw (payment debit)
    r = client.post(
        f"/accounts/{acc_number}/transactions",
        json={"amount": "500", "facility_type": 0},
    )
    assert r.status_code == 201, r.text
    assert r.json()["new_available_balance"] == "500.00"

    r = client.post(
        f"/accounts/{acc_number}/transactions",
        json={"amount": "-100", "facility_type": 496, "origin": "REGRESSION"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["new_available_balance"] == "400.00"

    # 5. Try to overdraw via PAYMENT — should be rejected.
    r = client.post(
        f"/accounts/{acc_number}/transactions",
        json={"amount": "-10000", "facility_type": 496},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["fail_code"] == "3"

    # 6. Update + delete account
    r = client.put(
        f"/accounts/{acc_number}",
        json={"interest_rate": "2.00", "overdraft_limit": 500},
    )
    assert r.status_code == 200, r.text
    assert r.json()["interest_rate"] == "2.00"

    r = client.delete(f"/accounts/{acc_number}")
    assert r.status_code == 200, r.text
    assert client.get(f"/accounts/{acc_number}").status_code == 404

    # 7. Delete customer
    r = client.delete(f"/customers/{cust_number}")
    assert r.status_code == 200, r.text
    assert client.get(f"/customers/{cust_number}").status_code == 404


def test_transfer_end_to_end(client):
    cust = client.post("/customers", json=_make_customer_payload("Owner")).json()
    a = client.post(
        "/accounts",
        json={"customer_number": cust["number"], "type": "CURRENT"},
    ).json()
    b = client.post(
        "/accounts",
        json={"customer_number": cust["number"], "type": "SAVING"},
    ).json()
    # Seed `a` with funds via teller credit so MORTGAGE/LOAN rules do not apply.
    client.post(
        f"/accounts/{a['number']}/transactions",
        json={"amount": "1000", "facility_type": 0},
    )

    r = client.post(
        "/transfers",
        json={"from_account": a["number"], "to_account": b["number"], "amount": "250"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["from_account"]["available_balance"] == "750.00"
    assert body["to_account"]["available_balance"] == "250.00"


def test_transfer_negative_amount_rejected_by_pydantic(client):
    """Pydantic guards the ``amount > 0`` rule at the boundary."""
    cust = client.post("/customers", json=_make_customer_payload("Owner2")).json()
    a = client.post(
        "/accounts", json={"customer_number": cust["number"], "type": "CURRENT"}
    ).json()
    b = client.post(
        "/accounts", json={"customer_number": cust["number"], "type": "SAVING"}
    ).json()
    r = client.post(
        "/transfers",
        json={"from_account": a["number"], "to_account": b["number"], "amount": "0"},
    )
    assert r.status_code == 422


def test_transfer_same_account_rejected(client):
    cust = client.post("/customers", json=_make_customer_payload("Owner3")).json()
    a = client.post(
        "/accounts", json={"customer_number": cust["number"], "type": "CURRENT"}
    ).json()
    r = client.post(
        "/transfers",
        json={"from_account": a["number"], "to_account": a["number"], "amount": "10"},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["fail_code"] == "5"


def test_customer_account_cap_returns_409(client):
    cust = client.post("/customers", json=_make_customer_payload("Cap")).json()
    for _ in range(10):
        r = client.post(
            "/accounts",
            json={"customer_number": cust["number"], "type": "CURRENT"},
        )
        assert r.status_code == 201, r.text
    r = client.post(
        "/accounts", json={"customer_number": cust["number"], "type": "CURRENT"}
    )
    assert r.status_code == 409
    assert r.json()["detail"]["fail_code"] == "8"


@pytest.mark.parametrize("acc_type", ["MORTGAGE", "LOAN"])
def test_payment_to_mortgage_or_loan_blocked(client, acc_type):
    cust = client.post("/customers", json=_make_customer_payload("LoanOwner")).json()
    acc = client.post(
        "/accounts",
        json={"customer_number": cust["number"], "type": acc_type},
    ).json()
    r = client.post(
        f"/accounts/{acc['number']}/transactions",
        json={"amount": "100", "facility_type": 496},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["fail_code"] == "4"
