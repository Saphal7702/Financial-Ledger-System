import sqlite3
from ..schemas.account import CreateAccountRequest, AccountResponse
from ..schemas.transaction import TransactionResponse
from ..schemas.ledger import LedgerEntryResponse
from ..db.db import connect
from fastapi import HTTPException
from .helpers import generate_id, utc_now
from .audit_service import log_event

def create_account(req: CreateAccountRequest) -> AccountResponse:
    account_id = generate_id()
    time_stamp = utc_now()

    try:
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO accounts(
                    id, account_code, owner_type, owner_id, account_type, currency, allow_negative,status, current_balance, created_at, updated_at
                ) values (?, ?, ?, ?, ? , ?, ?, ?, ?, ?, ?)
                """,
                (
                    account_id, 
                    req.account_code, 
                    req.owner_type, 
                    req.owner_id, 
                    req.account_type, 
                    req.currency.upper(), 
                    1 if req.allow_negative else 0, 
                    'active', 0, 
                    time_stamp, 
                    time_stamp
                )
            )
            log_event(
                conn=conn, 
                entity_type='account', 
                entity_id=account_id, 
                action='account_created',
            )
    except sqlite3.IntegrityError as e:
        if "account_code" in str(e):
            raise HTTPException(status_code=409, detail="account_code already exists")
        raise

    return get_account(account_id=account_id)

def get_account(account_id: str) -> AccountResponse:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM accounts WHERE id = ?
            """,
            (account_id, ),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return AccountResponse(
        id=row["id"], 
        account_code=row["account_code"], 
        owner_type=row["owner_type"], 
        owner_id=row["owner_id"], 
        account_type=row["account_type"], 
        currency=row["currency"],
        allow_negative=bool(row["allow_negative"]), 
        status=row["status"], 
        current_balance=row["current_balance"], 
        created_at=row["created_at"], 
        updated_at=row["updated_at"]
    )

def get_account_transactions(account_id: str) -> list[TransactionResponse]:
    transactions_list = []
    with connect() as conn:
        account_verify = conn.execute(
            """
            SELECT id FROM accounts WHERE id=?
            """,
            (account_id, ),
        ).fetchone()

        if not account_verify:
            raise HTTPException(status_code=404, detail="Account not found")

        transactions = conn.execute(
            """
            SELECT DISTINCT ts.*
            FROM transactions ts
            JOIN ledger_entries le ON le.transaction_id = ts.id
            WHERE le.account_id = ?
            ORDER BY ts.created_at DESC
            """,
            (account_id, ),
        ).fetchall()

        if not transactions:
            return []
        
        for trans in transactions:
            trans_resp = TransactionResponse(
                id=trans["id"],
                transaction_type=trans["transaction_type"],
                status=trans["status"],
                amount=trans["amount"],
                currency=trans["currency"],
                reference=trans["reference"],
                description=trans["description"],
                idempotency_key=trans["idempotency_key"],
                created_at=trans["created_at"],
                posted_at=trans["posted_at"]
            )
            transactions_list.append(trans_resp)

    return transactions_list

def get_account_entries(account_id: str) -> list[LedgerEntryResponse]:
    entries_list = []

    with connect() as conn:
        account_verify = conn.execute(
            """
            SELECT id FROM accounts WHERE id=?
            """,
            (account_id, ),
        ).fetchone()

        if not account_verify:
            raise HTTPException(status_code=404, detail="Account not found")
        
        ledger_entries = conn.execute(
            """
            SELECT * FROM ledger_entries WHERE account_id=? ORDER BY created_at DESC
            """,
            (account_id, ),
        ).fetchall()

        if not ledger_entries:
            return []
        
        for row in ledger_entries:
            entries_list.append(
                LedgerEntryResponse(
                    id=row["id"],
                    transaction_id=row["transaction_id"],
                    account_id=row["account_id"],
                    entry_type=row["entry_type"],
                    amount=row["amount"],
                    currency=row["currency"],
                    created_at=row["created_at"]
                )
            )

    return entries_list