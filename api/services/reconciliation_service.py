from ..schemas.reconciliation import AccountBalanceCheck, TransactionBalanceCheck
from ..db.db import connect
from fastapi import HTTPException

def verify_account_balances():
    accounts_list = []
    with connect() as conn:
        accounts = conn.execute(
            """
            SELECT id, account_code, currency, current_balance FROM accounts WHERE status='active'
            """
        ).fetchall()

        if not accounts:
            raise HTTPException(status_code=404, detail="No active accounts found")
        
        for acc in accounts:
            ledger_check = conn.execute(
                """
                SELECT 
                COALESCE(
                    SUM(
                        CASE 
                            WHEN entry_type='debit' THEN amount
                            WHEN entry_type='credit' THEN -amount
                            ELSE 0
                        END
                    ), 
                0) AS ledger_balance FROM ledger_entries WHERE account_id=?
                """,
                (acc["id"], ),
            ).fetchone()

            account_response = AccountBalanceCheck(
                account_id=acc["id"],
                account_code=acc["account_code"],
                currency=acc["currency"],
                cached_balance=acc["current_balance"],
                derived_balance=ledger_check["ledger_balance"],
                is_match=bool(acc["current_balance"] == ledger_check["ledger_balance"])
            )

            accounts_list.append(account_response)

    return accounts_list

def verify_transaction_balances():
    transactions_list = []

    with connect() as conn:
        transactions = conn.execute(
            """
            SELECT id, transaction_type, status FROM transactions
            """
        ).fetchall()

        if not transactions:
            raise HTTPException(status_code=404, detail="No transactions found")
        
        for trans in transactions:
            ledger_trans = conn.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN entry_type = 'debit' THEN amount ELSE 0 END), 0) AS debit_total,
                    COALESCE(SUM(CASE WHEN entry_type = 'credit' THEN amount ELSE 0 END), 0) AS credit_total
                FROM ledger_entries
                WHERE transaction_id = ?
                """,
                (trans["id"],),
            ).fetchone()

            transaction_response = TransactionBalanceCheck(
                transaction_id=trans["id"],
                transaction_type=trans["transaction_type"],
                status=trans["status"],
                debit_total=ledger_trans["debit_total"],
                credit_total=ledger_trans["credit_total"],
                is_balanced=bool(ledger_trans["debit_total"] == ledger_trans["credit_total"])
            )

            transactions_list.append(transaction_response)

    return transactions_list