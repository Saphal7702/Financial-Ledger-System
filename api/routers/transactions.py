from fastapi import APIRouter
from ..schemas.transaction import DepositRequest, WithdrawRequest, TransferRequest, TransactionResponse
from ..schemas.ledger import LedgerEntryResponse
from ..services import transaction_service

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.post("/deposit", response_model=TransactionResponse, status_code=201)
def deposit(req: DepositRequest):
    return transaction_service.deposit(req)

@router.post("/withdraw", response_model=TransactionResponse, status_code=201)
def withdraw(req: WithdrawRequest):
    return transaction_service.withdraw(req)

@router.post("/transfer", response_model=TransactionResponse, status_code=201)
def transfer(req: TransferRequest):
    return transaction_service.transfer(req)

@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: str):
    return transaction_service.get_transaction(transaction_id)

@router.get("/{transaction_id}/entries", response_model=list[LedgerEntryResponse])
def get_transaction_entries(transaction_id: str):
    return transaction_service.get_transaction_entires(transaction_id)