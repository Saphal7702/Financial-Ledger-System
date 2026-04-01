from pydantic import BaseModel
from typing import Optional

class DepositRequest(BaseModel):
    account_id: str
    amount: int
    currency: str
    idempotency_key: str

class WithdrawRequest(BaseModel):
    account_id: str
    amount: int
    currency: str
    idempotency_key: str

class TransferRequest(BaseModel):
    from_account_id: str
    to_account_id: str
    amount: int
    currency: str
    idempotency_key: str

class TransactionResponse(BaseModel):
    id: str
    transaction_type: str
    status: str
    amount: int
    currency: str
    reference: str | None = None
    description: str | None = None
    idempotency_key: str | None = None
    created_at: str
    posted_at: str | None = None