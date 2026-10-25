-- ==============================================================================
-- ARGUS Database Initialization Script
-- Architecture: Multi-Schema Zero-Trust Storage with Bitemporal Memory & Vector
-- ==============================================================================

-- 1. Enable Vector Extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Create Isolated Schemas
CREATE SCHEMA IF NOT EXISTS argus_core;
CREATE SCHEMA IF NOT EXISTS argus_memory;
CREATE SCHEMA IF NOT EXISTS argus_vault;

-- 3. Core Tables (argus_core)
CREATE TABLE IF NOT EXISTS argus_core.transactions (
    id VARCHAR(64) PRIMARY KEY,
    account_token VARCHAR(64) NOT NULL,
    counterparty_token VARCHAR(64) NOT NULL,
    amount NUMERIC(15, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'INR',
    timestamp TIMESTAMPTZ NOT NULL,
    channel VARCHAR(32) NOT NULL,
    device_id_token VARCHAR(64),
    ip_address_token VARCHAR(64),
    location_city VARCHAR(64),
    location_country VARCHAR(3) DEFAULT 'IND',
    narrative TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_txn_account ON argus_core.transactions(account_token);
CREATE INDEX IF NOT EXISTS idx_txn_counterparty ON argus_core.transactions(counterparty_token);
CREATE INDEX IF NOT EXISTS idx_txn_timestamp ON argus_core.transactions(timestamp DESC);

CREATE TABLE IF NOT EXISTS argus_core.decisions (
    id VARCHAR(64) PRIMARY KEY,
    transaction_id VARCHAR(64) REFERENCES argus_core.transactions(id),
    input_hash VARCHAR(64) NOT NULL,
    rule_bundle_ver VARCHAR(32) NOT NULL,
    model_ver VARCHAR(32) NOT NULL,
    risk_score NUMERIC(5, 4) NOT NULL,
    outcome VARCHAR(32) NOT NULL, -- ALLOW, HOLD, ESCALATE, BLOCK
    tier VARCHAR(10) NOT NULL,    -- T0, T1, T2, T3
    evidence_ids JSONB DEFAULT '[]'::jsonb,
    output_hash VARCHAR(64) NOT NULL,
    explanation_summary TEXT,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decisions_outcome ON argus_core.decisions(outcome);
CREATE INDEX IF NOT EXISTS idx_decisions_recorded_at ON argus_core.decisions(recorded_at DESC);

CREATE TABLE IF NOT EXISTS argus_core.cases (
    id VARCHAR(64) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    tier VARCHAR(10) NOT NULL,
    status VARCHAR(32) DEFAULT 'OPEN', -- OPEN, IN_REVIEW, APPROVED, REJECTED, CLOSED
    assigned_analyst VARCHAR(64),
    transaction_ids JSONB DEFAULT '[]'::jsonb,
    evidence_graph JSONB DEFAULT '{}'::jsonb,
    draft_narrative TEXT,
    analyst_verdict VARCHAR(32),
    analyst_notes TEXT,
    maker VARCHAR(64),
    checker VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS argus_core.audit_ledger (
    seq BIGSERIAL PRIMARY KEY,
    prev_hash VARCHAR(64) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR(64) NOT NULL,
    signer VARCHAR(64) NOT NULL,
    signature VARCHAR(128),
    payload JSONB NOT NULL,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_seq ON argus_core.audit_ledger(seq);

-- 4. Bitemporal Memory & Knowledge Tables (argus_memory)
CREATE TABLE IF NOT EXISTS argus_memory.bitemporal_facts (
    id BIGSERIAL PRIMARY KEY,
    subject VARCHAR(64) NOT NULL,       -- e.g. customer_token
    predicate VARCHAR(64) NOT NULL,     -- e.g. risk_category, kyc_status
    object JSONB NOT NULL,              -- factual payload
    valid_from TIMESTAMPTZ NOT NULL,    -- Business Time Start
    valid_to TIMESTAMPTZ NOT NULL,      -- Business Time End (infinity for current)
    recorded_at TIMESTAMPTZ DEFAULT NOW(), -- System Ingestion Time
    source VARCHAR(128) NOT NULL,
    classification VARCHAR(32) DEFAULT 'CONFIDENTIAL'
);

CREATE INDEX IF NOT EXISTS idx_facts_bitemporal ON argus_memory.bitemporal_facts(subject, valid_from, valid_to, recorded_at);

CREATE TABLE IF NOT EXISTS argus_memory.regulation_clauses (
    id VARCHAR(64) PRIMARY KEY,
    doc_id VARCHAR(64) NOT NULL,
    title VARCHAR(255) NOT NULL,
    chapter VARCHAR(128),
    section VARCHAR(128),
    clause_ref VARCHAR(64) NOT NULL,
    clause_text TEXT NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ DEFAULT '9999-12-31 23:59:59+00'::timestamptz,
    embedding vector(384),              -- matches BAAI/bge-small-en-v1.5 dimensions
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clauses_doc_ref ON argus_memory.regulation_clauses(doc_id, clause_ref);

-- 5. Isolated PII Vault (argus_vault)
CREATE TABLE IF NOT EXISTS argus_vault.tokens (
    token VARCHAR(64) PRIMARY KEY,
    kind VARCHAR(32) NOT NULL,          -- PAN, AADHAAR, ACCOUNT, PHONE, NAME, EMAIL
    ciphertext BYTEA NOT NULL,          -- AES-256-GCM encrypted raw PII
    nonce BYTEA NOT NULL,               -- 12-byte GCM initialization vector
    tag BYTEA NOT NULL,                 -- 16-byte authentication tag
    scope VARCHAR(64) NOT NULL,         -- session or customer scope
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vault_kind ON argus_vault.tokens(kind);
