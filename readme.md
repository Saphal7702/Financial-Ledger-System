Financial Ledger & Reconciliation Platform
A backend system that simulates how real-world financial platforms (banks, payment processors, trading systems) manage money using double-entry accounting, idempotent transactions, and reconciliation checks.

#Overview

This project implements a production-style financial ledger system with:

* Double-entry accounting (debit/credit model)
* Idempotent transaction processing (no duplicate postings)
* Atomic transaction handling
* Audit logging for traceability
* Reconciliation to verify system correctness
* Automated test suite

The system is built with Python + FastAPI + SQLite, and structured to support future migration to PostgreSQL.

#Core Concepts

1. Double-Entry Accounting
Every transaction generates balanced ledger entries. Total debits always equal total credits

| Transaction | Entries                          |
| ----------- | -------------------------------- |
| Deposit     | Debit user, Credit system        |
| Withdraw    | Credit user, Debit system        |
| Transfer    | Credit source, Debit destination |


2. Ledger vs Cached Balance
Cached balance equal the sum of ledger entries.
* ledger_entries → source of truth
* accounts.current_balance → cached balance


3. Idempotency
Each transaction request includes an idempotency_key. It prevents duplicate financial postings
* Same request + same key → returns same result
* Same key + different request → rejected

4. Atomic Transactions
All operations (ledger updates, balances, audit logs) occur in a single DB transaction. Either everything commits, or nothing does.

5. Reconciliation
System verifies correctness via:
* Account balance checks (ledger vs cached)
* Transaction balance checks (debits == credits)

6. Reversal
The ledger supports transaction reversal using compensating entries.
Instead of modifying or deleting an existing posted transaction, the system creates a new reversal transaction that offsets the original financial effect.
* original debit becomes reversal credit
* original credit becomes reversal debit

##API Endpoints

#Accounts
POST   /accounts
GET    /accounts/{account_id}
GET    /accounts/{account_id}/transactions
GET    /accounts/{account_id}/entries

#Transactions
POST   /transactions/deposit
POST   /transactions/withdraw
POST   /transactions/transfer
GET    /transactions/{transaction_id}
GET    /transactions/{transaction_id}/entries
POST /transactions/{transaction_id}/reverse

#Reconciliation
GET    /admin/reconciliation/accounts
GET    /admin/reconciliation/transactions

#Testing
Tests are implemented using pytest with an isolated temporary database per test.

#Key Invariants
The system enforces:
* Transactions are always balanced
* No duplicate transactions via idempotency
* Cached balance matches ledger-derived balance
* Only active accounts can transact
* Currency consistency across accounts
* Reversal transaction preservs original transaction

#Tech Stack
* Python 3.13
* FastAPI
* SQLite (designed for PostgreSQL migration)
* Pytest

#Author
Built as a portfolio project focused on transitioning into FinTech backend engineering.