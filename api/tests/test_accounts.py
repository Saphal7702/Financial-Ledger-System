def test_create_account_success(client):
    payload = {
        "account_code": "USER_1_WALLET",
        "owner_type": "user",
        "owner_id": "user_1",
        "account_type": "asset",
        "currency": "usd",
        "allow_negative": False,
    }

    resp = client.post("/accounts", json=payload)

    assert resp.status_code == 201

    data = resp.json()
    assert data["account_code"] == "USER_1_WALLET"
    assert data["owner_type"] == "user"
    assert data["owner_id"] == "user_1"
    assert data["account_type"] == "asset"
    assert data["currency"] == "USD"
    assert data["allow_negative"] is False
    assert data["current_balance"] == 0
    assert data["status"] == "active"
    assert "id" in data

def test_create_account_duplicate_code_returns_409(client):
    payload = {
        "account_code": "USER_1_WALLET",
        "owner_type": "user",
        "owner_id": "user_1",
        "account_type": "asset",
        "currency": "USD",
        "allow_negative": False,
    }

    first = client.post("/accounts", json=payload)
    second = client.post("/accounts", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "account_code already exists"