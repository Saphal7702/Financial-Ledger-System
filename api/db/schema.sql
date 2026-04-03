PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    account_code TEXT UNIQUE NOT NULL,
    owner_type TEXT NOT NULL CHECK (owner_type IN ('user', 'system', 'merchant')),
    owner_id TEXT NULL,
    account_type TEXT NOT NULL CHECK (account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')),
    currency TEXT NOT NULL,
    allow_negative INTEGER NOT NULL DEFAULT 0 CHECK (allow_negative IN (0, 1)),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'frozen', 'closed')),
    current_balance INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('deposit', 'withdraw', 'transfer', 'payment', 'reversal')),
    reference TEXT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'posted', 'failed', 'reversed')),
    amount INTEGER NOT NULL CHECK (amount > 0),
    currency TEXT NOT NULL,
    description TEXT NULL,
    idempotency_key TEXT NULL,
    created_at TEXT NOT NULL,
    posted_at TEXT NULL,
    reversal_of_transaction_id TEXT NULL
);

CREATE TABLE IF NOT EXISTS ledger_entries (
    id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    entry_type TEXT NOT NULL CHECK (entry_type IN ('debit', 'credit')),
    amount INTEGER NOT NULL CHECK (amount > 0),
    currency TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    key TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL,
    transaction_id TEXT NULL,
    status TEXT NOT NULL CHECK (status IN ('processing', 'completed', 'failed')),
    response_body TEXT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT NULL,
    metadata_json TEXT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ledger_entries_transaction_id
    ON ledger_entries(transaction_id);

CREATE INDEX IF NOT EXISTS idx_ledger_entries_account_id
    ON ledger_entries(account_id);

CREATE INDEX IF NOT EXISTS idx_transactions_created_at
    ON transactions(created_at);

CREATE INDEX IF NOT EXISTS idx_transactions_idempotency_key
    ON transactions(idempotency_key);

CREATE INDEX IF NOT EXISTS idx_accounts_owner
    ON accounts(owner_type, owner_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_idempotency_key_unique
    ON transactions(idempotency_key)
    WHERE idempotency_key IS NOT NULL;