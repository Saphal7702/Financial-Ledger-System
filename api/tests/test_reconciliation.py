def create_system_account(client):
    payload = {
        "account_code": "SYSTEM_CASH_CLEARING",
        "owner_type": "system",
        "owner_id": None,
        "account_type": "asset",
        "currency": "USD",
        "allow_negative": True,
    }
    return client.post("/accounts", json=payload)

def create_user_account(client, code="USER_1_WALLET", owner_id="user_1", allow_negative=False):
    payload = {
        "account_code": code,
        "owner_type": "user",
        "owner_id": owner_id,
        "account_type": "asset",
        "currency": "USD",
        "allow_negative": allow_negative,
    }
    return client.post("/accounts", json=payload)

def test_reconciliation_matches_after_valid_postings(client):
    create_system_account(client)
    acc_resp = create_user_account(client)
    account_id = acc_resp.json()["id"]

    deposit_payload = {
        "account_id": account_id,
        "amount": 5000,
        "currency": "USD",
        "idempotency_key": "dep-rec-001",
    }
    dep = client.post("/transactions/deposit", json=deposit_payload)
    assert dep.status_code == 201

    resp = client.get("/admin/reconciliation/accounts")
    assert resp.status_code == 200

    rows = resp.json()
    user_row = next(r for r in rows if r["account_id"] == account_id)

    assert user_row["cached_balance"] == 5000
    assert user_row["derived_balance"] == 5000
    assert user_row["is_match"] is True