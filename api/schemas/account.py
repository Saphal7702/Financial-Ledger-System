from pydantic import BaseModel
from typing import Literal

class CreateAccountRequest(BaseModel):
    account_code: str
    owner_type: Literal["user", "system", "merchant"]
    owner_id: str | None = None
    account_type: Literal["asset", "liability", "equity", "revenue", "expense"]
    currency: str
    allow_negative: bool = False

class AccountResponse(BaseModel):
    id: str
    account_code: str
    owner_type: str
    owner_id: str | None
    account_type: str
    currency: str
    allow_negative: bool
    status: str
    current_balance: int
    created_at: str
    updated_at: str