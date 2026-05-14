"""FastAPI integration tests for the GenApp insurance router."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _create_customer(client: TestClient, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "first_name": "Alice",
        "last_name": "Wong",
        "date_of_birth": "1985-03-12",
        "house_name": "Maple",
        "house_number": "12",
        "postcode": "SO21 2JN",
        "phone_mobile": "+44 7700 900001",
        "phone_home": "+44 1962 000001",
        "email_address": "alice@example.com",
    }
    body.update(overrides)
    resp = client.post("/insurance/customers", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_house_policy(
    client: TestClient, customer_number: int, **overrides: object
) -> dict[str, object]:
    body: dict[str, object] = {
        "customer_number": customer_number,
        "issue_date": "2024-06-01",
        "expiry_date": "2025-06-01",
        "broker_id": 42,
        "brokers_reference": "HOUSE-001",
        "payment": 450,
        "details": {
            "policy_type": "H",
            "property_type": "Detached",
            "bedrooms": 4,
            "value": 450000,
            "house_name": "Maple",
            "house_number": "12",
            "postcode": "SO21 2JN",
        },
    }
    body.update(overrides)
    resp = client.post("/insurance/policies", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_customer_lifecycle(client: TestClient) -> None:
    created = _create_customer(client)
    assert created["customer_number"] == 1

    got = client.get(f"/insurance/customers/{created['customer_number']}")
    assert got.status_code == 200
    assert got.json()["last_name"] == "Wong"

    upd = client.put(
        f"/insurance/customers/{created['customer_number']}",
        json={"phone_mobile": "+44 7700 999999"},
    )
    assert upd.status_code == 200
    assert upd.json()["phone_mobile"] == "+44 7700 999999"


def test_create_customer_validation_error(client: TestClient) -> None:
    resp = client.post(
        "/insurance/customers",
        json={"first_name": "X", "last_name": "Y"},  # missing date_of_birth
    )
    assert resp.status_code == 422


def test_get_missing_customer_404(client: TestClient) -> None:
    resp = client.get("/insurance/customers/9999")
    assert resp.status_code == 404


def test_policy_lifecycle_all_four_sub_types(client: TestClient) -> None:
    cust = _create_customer(client)
    cn = int(cust["customer_number"])

    endowment = client.post(
        "/insurance/policies",
        json={
            "customer_number": cn,
            "issue_date": "2024-01-15",
            "expiry_date": "2049-01-15",
            "broker_id": 42,
            "brokers_reference": "ENDOW-001",
            "payment": 350,
            "details": {
                "policy_type": "E",
                "with_profits": True,
                "equities": False,
                "managed_fund": True,
                "fund_name": "GROWTH",
                "term": 25,
                "sum_assured": 150000,
                "life_assured": "Alice Wong",
            },
        },
    )
    assert endowment.status_code == 201, endowment.text
    assert endowment.json()["policy_type"] == "E"
    assert endowment.json()["details"]["fund_name"] == "GROWTH"

    house = _create_house_policy(client, cn)
    assert house["policy_type"] == "H"
    assert house["details"]["value"] == 450000

    motor = client.post(
        "/insurance/policies",
        json={
            "customer_number": cn,
            "issue_date": "2024-03-10",
            "expiry_date": "2025-03-10",
            "details": {
                "policy_type": "M",
                "make": "Toyota",
                "model": "Corolla",
                "value": 18500,
                "reg_number": "AB12CDE",
                "colour": "SILVER",
                "cc": 1798,
                "manufactured": "2022-04",
                "premium": 620,
                "accidents": 0,
            },
        },
    )
    assert motor.status_code == 201, motor.text
    assert motor.json()["details"]["make"] == "Toyota"

    commercial = client.post(
        "/insurance/policies",
        json={
            "customer_number": cn,
            "issue_date": "2024-02-01",
            "expiry_date": "2025-02-01",
            "details": {
                "policy_type": "C",
                "address": "100 Bishopsgate, London",
                "postcode": "EC2A 4NE",
                "latitude": "51.5170",
                "longitude": "-0.0810",
                "customer_text": "Patel Catering Ltd",
                "prop_type": "Restaurant",
                "fire_peril": 80,
                "fire_premium": 1200,
                "crime_peril": 60,
                "crime_premium": 800,
                "flood_peril": 20,
                "flood_premium": 300,
                "weather_peril": 15,
                "weather_premium": 200,
                "status": 1,
                "reject_reason": "",
            },
        },
    )
    assert commercial.status_code == 201, commercial.text
    assert commercial.json()["details"]["fire_premium"] == 1200

    listing = client.get(f"/insurance/customers/{cn}/policies")
    assert listing.status_code == 200
    types = [p["policy_type"] for p in listing.json()]
    assert sorted(types) == ["C", "E", "H", "M"]


def test_update_policy_details(client: TestClient) -> None:
    cust = _create_customer(client)
    house = _create_house_policy(client, int(cust["customer_number"]))
    pn = int(house["policy_number"])

    upd = client.put(
        f"/insurance/policies/{pn}",
        json={
            "payment": 999,
            "details": {
                "policy_type": "H",
                "property_type": "Semi",
                "bedrooms": 3,
                "value": 300000,
                "house_name": "Oak",
                "house_number": "9",
                "postcode": "SO21 2JN",
            },
        },
    )
    assert upd.status_code == 200, upd.text
    body = upd.json()
    assert body["payment"] == 999
    assert body["details"]["property_type"] == "Semi"
    assert body["details"]["bedrooms"] == 3


def test_update_policy_cross_type_rejected(client: TestClient) -> None:
    cust = _create_customer(client)
    house = _create_house_policy(client, int(cust["customer_number"]))
    pn = int(house["policy_number"])

    upd = client.put(
        f"/insurance/policies/{pn}",
        json={
            "details": {
                "policy_type": "M",
                "make": "Honda",
                "model": "Civic",
                "value": 10000,
                "reg_number": "AA00AAA",
                "colour": "RED",
                "cc": 1500,
                "manufactured": "2020-01",
                "premium": 500,
                "accidents": 0,
            },
        },
    )
    assert upd.status_code == 409, upd.text
    assert upd.json()["detail"]["fail_code"] == "2"


def test_delete_policy(client: TestClient) -> None:
    cust = _create_customer(client)
    house = _create_house_policy(client, int(cust["customer_number"]))
    pn = int(house["policy_number"])

    resp = client.delete(f"/insurance/policies/{pn}")
    assert resp.status_code == 200, resp.text

    resp = client.get(f"/insurance/policies/{pn}")
    assert resp.status_code == 404


def test_claim_endpoints(client: TestClient) -> None:
    cust = _create_customer(client)
    house = _create_house_policy(client, int(cust["customer_number"]))
    pn = int(house["policy_number"])

    resp = client.post(
        "/insurance/claims",
        json={
            "policy_number": pn,
            "claim_date": "2024-12-01",
            "value": 5000,
            "paid": 4500,
            "cause": "Storm damage",
            "observations": "Quick settle",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["cause"] == "Storm damage"

    listing = client.get(f"/insurance/policies/{pn}/claims")
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_get_missing_policy_404(client: TestClient) -> None:
    resp = client.get("/insurance/policies/9999")
    assert resp.status_code == 404


def test_update_missing_policy_404(client: TestClient) -> None:
    resp = client.put("/insurance/policies/9999", json={"payment": 1})
    assert resp.status_code == 404


def test_delete_missing_policy_404(client: TestClient) -> None:
    resp = client.delete("/insurance/policies/9999")
    assert resp.status_code == 404


def test_update_missing_customer_404(client: TestClient) -> None:
    resp = client.put(
        "/insurance/customers/9999", json={"first_name": "Nobody"}
    )
    assert resp.status_code == 404


def test_list_policies_unknown_customer_404(client: TestClient) -> None:
    resp = client.get("/insurance/customers/9999/policies")
    assert resp.status_code == 404


def test_create_policy_unknown_customer_404(client: TestClient) -> None:
    resp = client.post(
        "/insurance/policies",
        json={
            "customer_number": 9999,
            "issue_date": "2024-01-01",
            "expiry_date": "2025-01-01",
            "details": {"policy_type": "H"},
        },
    )
    assert resp.status_code == 404


def test_create_claim_unknown_policy_404(client: TestClient) -> None:
    resp = client.post(
        "/insurance/claims",
        json={
            "policy_number": 9999,
            "claim_date": "2024-01-01",
            "value": 100,
        },
    )
    assert resp.status_code == 404


def test_list_claims_unknown_policy_404(client: TestClient) -> None:
    resp = client.get("/insurance/policies/9999/claims")
    assert resp.status_code == 404


def test_stats_endpoint(client: TestClient) -> None:
    cust = _create_customer(client)
    cn = int(cust["customer_number"])
    _create_house_policy(client, cn)
    client.get(f"/insurance/customers/{cn}")

    stats = client.get("/insurance/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert body["add_customer"] >= 1
    assert body["add_policy"] >= 1
    assert body["inquire_customer"] >= 1
