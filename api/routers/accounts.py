from fastapi import APIRouter
from ..schemas.account import CreateAccountRequest, AccountResponse
from ..schemas.ledger import LedgerEntryResponse
from ..schemas.transaction import TransactionResponse
from ..services import account_service

router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.post("", response_model=AccountResponse, status_code=201)
def create_acc(req: CreateAccountRequest):
    return account_service.create_account(req)

@router.get("/{account_id}", response_model=AccountResponse)
def get_acc(account_id: str):
    return account_service.get_account(account_id)

@router.get("/{account_id}/transactions", response_model=list[TransactionResponse])
def get_acc_transactions(account_id: str):
    return account_service.get_account_transactions(account_id)

@router.get("/{account_id}/entries", response_model=list[LedgerEntryResponse])
def get_acc_entries(account_id: str):
    return account_service.get_account_entries(account_id)