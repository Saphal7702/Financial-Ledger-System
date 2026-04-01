from pydantic import BaseModel

class LedgerEntryResponse(BaseModel):
    id: str
    transaction_id: str
    account_id: str
    entry_type: str
    amount: int
    currency: str
    created_at: str