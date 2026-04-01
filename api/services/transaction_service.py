from ..schemas.transaction import DepositRequest, WithdrawRequest, TransferRequest, TransactionResponse
from ..schemas.ledger import LedgerEntryResponse
from fastapi import HTTPException
from ..db.db import connect
from .helpers import generate_id, utc_now, make_request_hash
from .audit_service import log_event

def _insert_transaction(conn, transaction_id, transaction_type, status, amount, currency, idempotency_key, created_at) -> None:
    conn.execute(
            """
            INSERT INTO transactions (
                id, transaction_type, status, amount, currency, idempotency_key, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transaction_id,
                transaction_type,
                status,
                amount,
                currency,
                idempotency_key,
                created_at
            )
        )
    
def _insert_ledger_entry(conn, ledger_id, transaction_id, account_id, entry_type, amount, currency, created_at) -> None:
    conn.execute(
            """
            INSERT INTO ledger_entries (
                id, transaction_id, account_id, entry_type, amount, currency, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,(
                ledger_id,
                transaction_id,
                account_id,
                entry_type,
                amount,
                currency,
                created_at
            )
        )
    
def _record_idempotency(conn, key, request_hash, transaction_id, status, created_at, updated_at) -> None:
    conn.execute(
            """
            INSERT INTO idempotency_keys(
                key, request_hash, transaction_id, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,(
                key,
                request_hash,
                transaction_id,
                status,
                created_at,
                updated_at
            )
        )
    
def _get_existing_idempotent_transaction(conn, idempotency_key):
    return conn.execute(
            """
            SELECT request_hash, transaction_id FROM idempotency_keys where key=?
            """,
            (idempotency_key,),
        ).fetchone()
    
def _load_system_cash_account(conn):
    system_code = "SYSTEM_CASH_CLEARING"
    return conn.execute(
                """
                SELECT id, currency, status from accounts where account_code=?
                """,
                (system_code, ),
            ).fetchone()

def _update_balance(conn, amount, account_id, action) -> None:
    if action == 'add':
        conn.execute(
            """
            UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?
            """,
            (amount, account_id)
        )
    elif action == "sub":
        conn.execute(
            """
            UPDATE accounts SET current_balance = current_balance - ? WHERE id = ?
            """,
            (amount, account_id)
        )
    else:
        raise ValueError("Invalid balance update action")

def _complete_transaction(conn, posted_at, id) -> None:
    conn.execute(
            """
            UPDATE transactions SET status='posted', posted_at = ? WHERE id=?
            """,
            (posted_at, id)
        )

def deposit(req: DepositRequest) -> TransactionResponse:
    transaction_id = generate_id()
    time_stamp = utc_now()

    ledger_id1 = generate_id()
    ledger_id2 = generate_id()

    currency = req.currency.upper()

    request_hash = make_request_hash({
        "type": "deposit",
        "account_id": req.account_id,
        "amount": req.amount,
        "currency": currency,
    })

    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")

    with connect() as conn:

        existing_idempotency = _get_existing_idempotent_transaction(conn, req.idempotency_key)

        if existing_idempotency:
            if existing_idempotency["request_hash"] != request_hash:
                raise HTTPException(status_code=409, detail="Idempotency key reuse with different request payload")
            return get_transaction(existing_idempotency["transaction_id"])

        dest_acc = conn.execute(
            """
            SELECT id, currency, status from accounts where id=?
            """, 
            (req.account_id,),
        ).fetchone()

        if not dest_acc:
            raise HTTPException(status_code=404, detail="Destination account not found")
        
        sys_acc = _load_system_cash_account(conn)

        if not sys_acc:
            raise HTTPException(status_code=409, detail="System cash account not found")
        
        if dest_acc["currency"] != currency:
            raise HTTPException(status_code=400, detail="Destination account currency mismatch")

        if sys_acc["currency"] != currency:
            raise HTTPException(status_code=409, detail="System cash account currency mismatch")
        
        if dest_acc["status"] != "active":
            raise HTTPException(status_code=409, detail="Destination account is not active")
        
        if sys_acc["status"] != "active":
            raise HTTPException(status_code=409, detail="System account is not active")

        _insert_transaction(conn, transaction_id, 'deposit', 'pending', req.amount, currency, req.idempotency_key, time_stamp)

        _insert_ledger_entry(conn, ledger_id1, transaction_id, req.account_id, 'debit', req.amount, currency, time_stamp)
        _insert_ledger_entry(conn, ledger_id2, transaction_id, sys_acc["id"], 'credit', req.amount, currency, time_stamp)

        _update_balance(conn, req.amount, req.account_id, 'add')
        _update_balance(conn, req.amount, sys_acc["id"], 'sub')

        _complete_transaction(conn, time_stamp, transaction_id)

        _record_idempotency(conn, req.idempotency_key, request_hash, transaction_id,  'completed', time_stamp, time_stamp)

        log_event(
            conn=conn, 
            entity_type='transaction', 
            entity_id=transaction_id, 
            action='deposit_posted',
            metadata={
                "account_id": req.account_id,
                "amount": req.amount,
                "currency": currency,
            }
        )

    return get_transaction(transaction_id=transaction_id)

def withdraw(req: WithdrawRequest) -> TransactionResponse:
    transaction_id = generate_id()
    time_stamp = utc_now()

    ledger_id1 = generate_id()
    ledger_id2 = generate_id()

    currency = req.currency.upper()

    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    
    request_hash = make_request_hash({
        "type": "withdraw",
        "account_id": req.account_id,
        "amount": req.amount,
        "currency": currency,
    })

    with connect() as conn:
        existing_idempotency = _get_existing_idempotent_transaction(conn, req.idempotency_key)

        if existing_idempotency:
            if existing_idempotency["request_hash"] != request_hash:
                raise HTTPException(status_code=409, detail="Idempotency key reuse with different request payload")
            return get_transaction(existing_idempotency["transaction_id"])
        
        dest_acc = conn.execute(
            """
            SELECT id, currency, status, current_balance, allow_negative FROM accounts WHERE id=?
            """,
            (req.account_id,),
        ).fetchone()

        if not dest_acc:
            raise HTTPException(status_code=404, detail="Requested account not found")
        
        if not bool(dest_acc["allow_negative"]) and dest_acc["current_balance"] < req.amount:
            raise HTTPException(status_code=409, detail="Insufficient funds")
        
        if dest_acc["currency"] != currency:
            raise HTTPException(status_code=400, detail="Requested account currency mismatch")
        
        if dest_acc["status"] != "active":
            raise HTTPException(status_code=409, detail="Requested account is not active")
        
        sys_acc = _load_system_cash_account(conn)

        if not sys_acc:
            raise HTTPException(status_code=404, detail="System account not found")
        
        if sys_acc["currency"] != currency:
            raise HTTPException(status_code=409, detail="System account currency mismatch")
        
        if sys_acc["status"] != "active":
            raise HTTPException(status_code=409, detail="System account is not active")
        
        _insert_transaction(conn, transaction_id, 'withdraw', 'pending', req.amount, currency, req.idempotency_key, time_stamp)

        _insert_ledger_entry(conn, ledger_id1, transaction_id, req.account_id, 'credit', req.amount, currency, time_stamp)
        _insert_ledger_entry(conn, ledger_id2, transaction_id, sys_acc["id"], 'debit', req.amount, currency, time_stamp)

        _update_balance(conn, req.amount, req.account_id, 'sub')
        _update_balance(conn, req.amount, sys_acc["id"], 'add')

        _complete_transaction(conn, time_stamp, transaction_id)

        _record_idempotency(conn, req.idempotency_key, request_hash, transaction_id,  'completed', time_stamp, time_stamp)

        log_event(
            conn=conn, 
            entity_type='transaction', 
            entity_id=transaction_id, 
            action='withdraw_posted',
            metadata={
                "account_id": req.account_id,
                "amount": req.amount,
                "currency": currency,
            }
        )
    
    return get_transaction(transaction_id=transaction_id)

def transfer(req: TransferRequest) -> TransactionResponse:
    transaction_id = generate_id()
    time_stamp = utc_now()

    ledger_id1 = generate_id()
    ledger_id2 = generate_id()

    currency = req.currency.upper()

    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0")
    
    if req.from_account_id == req.to_account_id:
        raise HTTPException(status_code=400, detail="Source and destination accounts must be different")

    request_hash = make_request_hash({
        "type": "transfer",
        "from_account_id": req.from_account_id,
        "to_account_id": req.to_account_id,
        "amount": req.amount,
        "currency": currency,
    })

    with connect() as conn:
        existing_idempotency = _get_existing_idempotent_transaction(conn, req.idempotency_key)

        if existing_idempotency:
            if existing_idempotency["request_hash"] != request_hash:
                raise HTTPException(status_code=409, detail="Idempotency key reuse with different request payload")
            return(get_transaction(existing_idempotency["transaction_id"]))
        
        source_acc = conn.execute(
            """
            SELECT id, currency, status, current_balance, allow_negative FROM accounts WHERE id=? 
            """,
            (req.from_account_id,),
        ).fetchone()

        if not source_acc:
            raise HTTPException(status_code=404, detail="Source account not found")
        
        if source_acc["status"] != "active":
            raise HTTPException(status_code=409, detail="Source account is not active")
        
        if source_acc["currency"] != currency:
            raise HTTPException(status_code=400, detail="Source account currency mismatch")
        
        if not bool(source_acc["allow_negative"]) and source_acc["current_balance"] < req.amount:
            raise HTTPException(status_code=409, detail="Insufficient funds")
        
        dest_acc = conn.execute(
            """
            SELECT id, currency, status FROM accounts WHERE id=?
            """,
            (req.to_account_id,),
        ).fetchone()

        if not dest_acc:
            raise HTTPException(status_code=404, detail="Destination account not found")
        
        if dest_acc["status"] != "active":
            raise HTTPException(status_code=409, detail="Destination account is not active")
        
        if dest_acc["currency"] != currency:
            raise HTTPException(status_code=400, detail="Destination account currency mismatch")
        
        _insert_transaction(conn, transaction_id, 'transfer', 'pending', req.amount, currency, req.idempotency_key, time_stamp)

        _insert_ledger_entry(conn, ledger_id1, transaction_id, req.from_account_id, 'credit', req.amount, currency, time_stamp)
        _insert_ledger_entry(conn, ledger_id2, transaction_id, req.to_account_id, 'debit', req.amount, currency, time_stamp)

        _update_balance(conn, req.amount, source_acc["id"], 'sub')
        _update_balance(conn, req.amount, dest_acc["id"], 'add')

        _complete_transaction(conn, time_stamp, transaction_id)

        _record_idempotency(conn, req.idempotency_key, request_hash, transaction_id,  'completed', time_stamp, time_stamp)

        log_event(
            conn=conn, 
            entity_type='transaction', 
            entity_id=transaction_id, 
            action='transfer_posted',
            metadata={
                "from_account_id": req.from_account_id,
                "to_account_id": req.to_account_id,
                "amount": req.amount,
                "currency": currency,
            }
        )

    return get_transaction(transaction_id)

def get_transaction(transaction_id: str) -> TransactionResponse:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM transactions WHERE id = ?
            """,
            (transaction_id,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    return TransactionResponse(
        id=row["id"],
        transaction_type=row["transaction_type"],
        status=row["status"],
        amount=row["amount"],
        currency=row["currency"],
        reference=row["reference"],
        description=row["description"],
        idempotency_key=row["idempotency_key"],
        created_at=row["created_at"],
        posted_at=row["posted_at"]
    )

def get_transaction_entries(transaction_id: str) -> list[LedgerEntryResponse]:
    entries_list = []

    with connect() as conn:

        tx = conn.execute(
            "SELECT id FROM transactions WHERE id = ?",
            (transaction_id,),
        ).fetchone()

        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found")

        rows = conn.execute(
            """
            SELECT * FROM ledger_entries WHERE transaction_id=? ORDER BY created_at DESC
            """,
            (transaction_id, ),
        ).fetchall()

        if not rows:
            return []

        for row in rows:
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