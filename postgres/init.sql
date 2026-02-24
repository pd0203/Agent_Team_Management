-- ============================================================
-- Hyojin Distribution AI Agent Team — PostgreSQL Schema
-- ============================================================
-- Initializes all tables required for:
--   1. Conversation history (persistent memory per chat)
--   2. API usage logging (BudgetGuard cost tracking)
--   3. Aggregate views for daily/monthly reporting
-- ============================================================

-- ============================================================
-- 1. messages — Stores all conversation turns (CEO ↔ agents)
--    Used to provide context in subsequent LLM calls.
-- ============================================================
CREATE TABLE IF NOT EXISTS messages (
    id          BIGSERIAL PRIMARY KEY,
    chat_id     BIGINT      NOT NULL,            -- Telegram chat ID
    role        VARCHAR(20) NOT NULL             -- 'user' | 'model'
                CHECK (role IN ('user', 'model')),
    content     TEXT        NOT NULL,
    agent_name  VARCHAR(50),                     -- which agent produced this
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messages_chat_created
    ON messages (chat_id, created_at DESC);

-- ============================================================
-- 2. api_usage_log — Records every LLM API call.
--    BudgetGuard reads this before and after each call.
-- ============================================================
CREATE TABLE IF NOT EXISTS api_usage_log (
    id              BIGSERIAL PRIMARY KEY,
    called_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    agent_name      VARCHAR(50) NOT NULL,        -- e.g. 'chief_secretary'
    model_name      VARCHAR(100) NOT NULL,       -- e.g. 'gemini-3.0-flash-001'
    input_tokens    INTEGER     NOT NULL DEFAULT 0,
    output_tokens   INTEGER     NOT NULL DEFAULT 0,
    total_tokens    INTEGER     NOT NULL GENERATED ALWAYS AS
                        (input_tokens + output_tokens) STORED,
    cost_usd        NUMERIC(12, 8) NOT NULL DEFAULT 0, -- precise USD cost
    cost_krw        NUMERIC(14, 2) NOT NULL DEFAULT 0, -- KRW equivalent
    date_kst        DATE        NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Seoul')::DATE
);

CREATE INDEX IF NOT EXISTS idx_api_usage_date
    ON api_usage_log (date_kst);

CREATE INDEX IF NOT EXISTS idx_api_usage_called_at
    ON api_usage_log (called_at DESC);

-- ============================================================
-- 3. daily_cost_summary — View for quick daily cost reporting
-- ============================================================
CREATE OR REPLACE VIEW daily_cost_summary AS
SELECT
    date_kst                            AS date,
    COUNT(*)                            AS api_calls,
    SUM(input_tokens)                   AS total_input_tokens,
    SUM(output_tokens)                  AS total_output_tokens,
    SUM(total_tokens)                   AS total_tokens,
    ROUND(SUM(cost_usd)::NUMERIC, 6)    AS total_cost_usd,
    ROUND(SUM(cost_krw)::NUMERIC, 0)    AS total_cost_krw
FROM api_usage_log
GROUP BY date_kst
ORDER BY date_kst DESC;

-- ============================================================
-- 4. monthly_cost_summary — View for monthly budget tracking
-- ============================================================
CREATE OR REPLACE VIEW monthly_cost_summary AS
SELECT
    DATE_TRUNC('month', called_at AT TIME ZONE 'Asia/Seoul')::DATE AS month,
    COUNT(*)                                AS api_calls,
    SUM(total_tokens)                       AS total_tokens,
    ROUND(SUM(cost_usd)::NUMERIC, 4)        AS total_cost_usd,
    ROUND(SUM(cost_krw)::NUMERIC, 0)        AS total_cost_krw
FROM api_usage_log
GROUP BY DATE_TRUNC('month', called_at AT TIME ZONE 'Asia/Seoul')
ORDER BY month DESC;

-- ============================================================
-- 5. budget_alerts_log — Records when budget threshold alerts
--    were sent, to prevent duplicate notifications.
-- ============================================================
CREATE TABLE IF NOT EXISTS budget_alerts_log (
    id          BIGSERIAL PRIMARY KEY,
    alert_type  VARCHAR(30) NOT NULL,   -- 'daily_70', 'daily_90', 'daily_100', 'monthly_100'
    date_kst    DATE        NOT NULL DEFAULT (NOW() AT TIME ZONE 'Asia/Seoul')::DATE,
    sent_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (alert_type, date_kst)       -- only one alert per type per day
);

-- ============================================================
-- 6. Seed: ensure tables are ready (no-op if already exist)
-- ============================================================
SELECT 'Schema initialization complete' AS status;
