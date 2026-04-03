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


def test_reverse_deposit_restores_balances(client):
    create_system_account(client)
    acc_resp = create_user_account(client)
    account_id = acc_resp.json()["id"]

    deposit_payload = {
        "account_id": account_id,
        "amount": 5000,
        "currency": "USD",
        "idempotency_key": "dep-rev-001",
    }

    dep_resp = client.post("/transactions/deposit", json=deposit_payload)
    assert dep_resp.status_code == 201
    original_tx = dep_resp.json()
    original_tx_id = original_tx["id"]

    reverse_payload = {
        "idempotency_key": "rev-001"
    }

    rev_resp = client.post(f"/transactions/{original_tx_id}/reverse", json=reverse_payload)
    assert rev_resp.status_code == 201

    reversal_tx = rev_resp.json()
    assert reversal_tx["transaction_type"] == "reversal"
    assert reversal_tx["status"] == "posted"
    assert reversal_tx["reversal_of_transaction_id"] == original_tx_id
    assert reversal_tx["amount"] == 5000
    assert reversal_tx["currency"] == "USD"

    acc_check = client.get(f"/accounts/{account_id}")
    assert acc_check.status_code == 200
    assert acc_check.json()["current_balance"] == 0

    rec_resp = client.get("/admin/reconciliation/accounts")
    assert rec_resp.status_code == 200
    rows = rec_resp.json()

    user_row = next(r for r in rows if r["account_id"] == account_id)
    assert user_row["cached_balance"] == 0
    assert user_row["derived_balance"] == 0
    assert user_row["is_match"] is True


def test_reverse_same_transaction_twice_returns_same_reversal(client):
    create_system_account(client)
    acc_resp = create_user_account(client)
    account_id = acc_resp.json()["id"]

    deposit_payload = {
        "account_id": account_id,
        "amount": 5000,
        "currency": "USD",
        "idempotency_key": "dep-rev-002",
    }

    dep_resp = client.post("/transactions/deposit", json=deposit_payload)
    assert dep_resp.status_code == 201
    original_tx_id = dep_resp.json()["id"]

    first_reverse = client.post(
        f"/transactions/{original_tx_id}/reverse",
        json={"idempotency_key": "rev-002"},
    )
    second_reverse = client.post(
        f"/transactions/{original_tx_id}/reverse",
        json={"idempotency_key": "rev-003"},
    )

    assert first_reverse.status_code == 201
    assert second_reverse.status_code == 201

    first_data = first_reverse.json()
    second_data = second_reverse.json()

    assert first_data["id"] == second_data["id"]
    assert first_data["reversal_of_transaction_id"] == original_tx_id
    assert second_data["reversal_of_transaction_id"] == original_tx_id


def test_cannot_reverse_a_reversal_transaction(client):
    create_system_account(client)
    acc_resp = create_user_account(client)
    account_id = acc_resp.json()["id"]

    deposit_payload = {
        "account_id": account_id,
        "amount": 5000,
        "currency": "USD",
        "idempotency_key": "dep-rev-004",
    }

    dep_resp = client.post("/transactions/deposit", json=deposit_payload)
    assert dep_resp.status_code == 201
    original_tx_id = dep_resp.json()["id"]

    rev_resp = client.post(
        f"/transactions/{original_tx_id}/reverse",
        json={"idempotency_key": "rev-004"},
    )
    assert rev_resp.status_code == 201

    reversal_tx_id = rev_resp.json()["id"]

    reverse_reversal = client.post(
        f"/transactions/{reversal_tx_id}/reverse",
        json={"idempotency_key": "rev-005"},
    )

    assert reverse_reversal.status_code == 409
    assert reverse_reversal.json()["detail"] == "Reversal transactions cannot be reversed"


def test_reconciliation_still_passes_after_reversal(client):
    create_system_account(client)
    source_resp = create_user_account(client, code="USER_REV_WALLET", owner_id="user_rev")
    account_id = source_resp.json()["id"]

    deposit_payload = {
        "account_id": account_id,
        "amount": 7000,
        "currency": "USD",
        "idempotency_key": "dep-rev-006",
    }

    dep_resp = client.post("/transactions/deposit", json=deposit_payload)
    assert dep_resp.status_code == 201
    original_tx_id = dep_resp.json()["id"]

    rev_resp = client.post(
        f"/transactions/{original_tx_id}/reverse",
        json={"idempotency_key": "rev-006"},
    )
    assert rev_resp.status_code == 201

    acc_rec = client.get("/admin/reconciliation/accounts")
    tx_rec = client.get("/admin/reconciliation/transactions")

    assert acc_rec.status_code == 200
    assert tx_rec.status_code == 200

    acc_rows = acc_rec.json()
    tx_rows = tx_rec.json()

    user_row = next(r for r in acc_rows if r["account_id"] == account_id)
    assert user_row["cached_balance"] == 0
    assert user_row["derived_balance"] == 0
    assert user_row["is_match"] is True

    original_tx_row = next(r for r in tx_rows if r["transaction_id"] == original_tx_id)
    reversal_tx_row = next(
        r for r in tx_rows if r["transaction_id"] == rev_resp.json()["id"]
    )

    assert original_tx_row["is_balanced"] is True
    assert reversal_tx_row["is_balanced"] is True