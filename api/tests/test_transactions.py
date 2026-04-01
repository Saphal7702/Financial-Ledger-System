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

def test_deposit_success(client):
    create_system_account(client)
    acc_resp = create_user_account(client)

    account_id = acc_resp.json()["id"]

    deposit_payload = {
        "account_id" : account_id,
        "amount": 5000,
        "currency": "usd",
        "idempotency_key": "dep-test-001"
    }

    resp = client.post("/transactions/deposit", json=deposit_payload)

    assert resp.status_code == 201

    data = resp.json()

    assert data["transaction_type"] == "deposit"
    assert data["status"] == "posted"
    assert data["amount"] == 5000
    assert data["currency"] == "USD"

    acc_check = client.get(f"/accounts/{account_id}")
    assert acc_check.status_code == 200
    assert acc_check.json()["current_balance"] == 5000

def test_deposit_idempotency_replay_returns_same_transaction(client):
    create_system_account(client)
    acc_resp = create_user_account(client)
    account_id = acc_resp.json()["id"]

    payload = {
        "account_id": account_id,
        "amount": 5000,
        "currency": "USD",
        "idempotency_key": "dep-test-001",
    }

    first = client.post("/transactions/deposit", json=payload)
    second = client.post("/transactions/deposit", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201

    first_data = first.json()
    second_data = second.json()

    assert first_data["id"] == second_data["id"]

    acc_check = client.get(f"/accounts/{account_id}")
    assert acc_check.json()["current_balance"] == 5000

def test_deposit_idempotency_mismatch_returns_409(client):
    create_system_account(client)
    acc_resp = create_user_account(client)
    account_id = acc_resp.json()["id"]

    first_payload = {
        "account_id": account_id,
        "amount": 5000,
        "currency": "USD",
        "idempotency_key": "same-key",
    }

    second_payload = {
        "account_id": account_id,
        "amount": 7000,
        "currency": "USD",
        "idempotency_key": "same-key",
    }

    first = client.post("/transactions/deposit", json=first_payload)
    second = client.post("/transactions/deposit", json=second_payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert "Idempotency key reuse" in second.json()["detail"]

def test_withdraw_insufficient_funds_returns_409(client):
    create_system_account(client)
    acc_resp = create_user_account(client)
    account_id = acc_resp.json()["id"]

    payload = {
        "account_id": account_id,
        "amount": 1000,
        "currency": "USD",
        "idempotency_key": "wd-test-001",
    }

    resp = client.post("/transactions/withdraw", json=payload)

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Insufficient funds"

def test_transfer_success(client):
    create_system_account(client)

    source = create_user_account(client, code="USER_A_WALLET", owner_id="user_a")
    dest = create_user_account(client, code="USER_B_WALLET", owner_id="user_b")

    source_id = source.json()["id"]
    dest_id = dest.json()["id"]

    deposit_payload = {
        "account_id": source_id,
        "amount": 8000,
        "currency": "USD",
        "idempotency_key": "dep-source-001",
    }
    dep = client.post("/transactions/deposit", json=deposit_payload)
    assert dep.status_code == 201

    transfer_payload = {
        "from_account_id": source_id,
        "to_account_id": dest_id,
        "amount": 3000,
        "currency": "USD",
        "idempotency_key": "tr-test-001",
    }

    tr = client.post("/transactions/transfer", json=transfer_payload)
    assert tr.status_code == 201
    tr_data = tr.json()
    assert tr_data["transaction_type"] == "transfer"
    assert tr_data["status"] == "posted"

    source_check = client.get(f"/accounts/{source_id}")
    dest_check = client.get(f"/accounts/{dest_id}")

    assert source_check.json()["current_balance"] == 5000
    assert dest_check.json()["current_balance"] == 3000