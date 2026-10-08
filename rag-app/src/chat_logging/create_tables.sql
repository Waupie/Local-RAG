-- create_tables.sql
-- Creates the chat_messages and visits tables.
-- Safe to run multiple times (uses IF NOT EXISTS).

-- Stores raw user chat queries (see chat_logging/save_message)
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Stores privacy-friendly, deduplicated daily visit records
-- (see chat_logging/save_visit and the /track-visit endpoint)
CREATE TABLE IF NOT EXISTS visits (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    hour INTEGER NOT NULL,
    path TEXT,
    referrer_domain TEXT,
    device TEXT,
    browser TEXT,
    visitor_hash TEXT NOT NULL,
    UNIQUE (visitor_hash, date)
);

-- Helpful index for the common "unique visitors per day" query
CREATE INDEX IF NOT EXISTS idx_visits_date ON visits (date);