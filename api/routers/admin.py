from fastapi import APIRouter
from ..schemas.reconciliation import AccountBalanceCheck, TransactionBalanceCheck
from ..services.reconciliation_service import verify_account_balances, verify_transaction_balances

router = APIRouter(prefix="/admin/reconciliation", tags=["reconciliation"])

@router.get("/accounts", response_model=list[AccountBalanceCheck])
def verify_acc_balances():
    return verify_account_balances()

@router.get("/transactions", response_model=list[TransactionBalanceCheck])
def verify_trans_balances():
    return verify_transaction_balances()