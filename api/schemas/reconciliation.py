from pydantic import BaseModel

class AccountBalanceCheck(BaseModel):
    account_id: str
    account_code: str
    currency: str
    cached_balance: int
    derived_balance: int
    is_match: bool

class TransactionBalanceCheck(BaseModel):
    transaction_id: str
    transaction_type: str
    status: str
    debit_total: int
    credit_total: int
    is_balanced: bool