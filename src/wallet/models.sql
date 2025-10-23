-- accounts: 각 사용자 계정(샤딩 키 예: account_id)
CREATE TABLE IF NOT EXISTS accounts (
  account_id BIGINT PRIMARY KEY,
  ccy        TEXT NOT NULL DEFAULT 'USDT',
  balance    NUMERIC(38,18) NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ledger: 거래 원장 (이벤트 소싱)
CREATE TABLE IF NOT EXISTS ledger (
  ledger_id  BIGSERIAL PRIMARY KEY,
  account_id BIGINT NOT NULL,
  ccy        TEXT NOT NULL,
  delta      NUMERIC(38,18) NOT NULL,
  ref_type   TEXT NOT NULL,      -- e.g. 'trade'
  ref_id     TEXT NOT NULL,      -- trade_id
  ts_ms      BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- idempotency: 같은 trade_id 반복 처리 방지 (unique)
CREATE TABLE IF NOT EXISTS processed_trades (
  trade_id TEXT PRIMARY KEY,
  account_id BIGINT NOT NULL,    -- (예) 심플 데모: 1계정 가정 / 실제는 심볼/포지션 테이블 매핑
  qty      NUMERIC(38,18) NOT NULL,
  price    NUMERIC(38,18) NOT NULL,
  ts_ms    BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ledger_account ON ledger (account_id);
