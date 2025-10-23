import asyncpg
from .metrics import DB_ERRORS_TOTAL
from typing import Optional

_pool: Optional[asyncpg.pool.Pool] = None

async def init_pool(dsn: str):
    global _pool
    _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=10)

async def close_pool():
    global _pool
    if _pool: await _pool.close()

async def apply_trade(trade: dict) -> bool:
    """
    trade: {trade_id, order_id, symbol, side, price, qty, ts}
    idempotent 처리: processed_trades(trade_id) UNIQUE
    balance update: accounts.balance += delta (buy:+, sell:-) — 데모
    ledger 삽입: 불변 원장
    """
    assert _pool is not None
    # DEMO: 모든 체결은 account_id=1로 가정 (면접용 데모)
    account_id = 1
    qty = float(trade["qty"])
    side = trade["side"].lower()
    delta = qty if side == "buy" else -qty
    ccy = "USDT"
    trade_id = trade["trade_id"]
    price = float(trade["price"])
    ts_ms = int(trade["ts"])

    async with _pool.acquire() as conn:
        tr = conn.transaction(isolation="repeatable_read")
        await tr.start()
        try:
            # idem check
            exists = await conn.fetchval("SELECT 1 FROM processed_trades WHERE trade_id=$1", trade_id)
            if exists:
                await tr.rollback()
                return False

            # lock account row
            acc = await conn.fetchrow("SELECT balance FROM accounts WHERE account_id=$1 FOR UPDATE", account_id)
            if acc is None:
                await conn.execute("INSERT INTO accounts(account_id, ccy, balance) VALUES ($1,$2,0)", account_id, ccy)
                bal = 0.0
            else:
                bal = float(acc["balance"])

            new_bal = bal + delta
            # ledger insert
            await conn.execute(
                "INSERT INTO ledger(account_id, ccy, delta, ref_type, ref_id, ts_ms) VALUES ($1,$2,$3,$4,$5,$6)",
                account_id, ccy, delta, "trade", trade_id, ts_ms
            )
            # account update
            await conn.execute("UPDATE accounts SET balance=$1, updated_at=now() WHERE account_id=$2",
                               new_bal, account_id)
            # idem record
            await conn.execute(
                "INSERT INTO processed_trades(trade_id, account_id, qty, price, ts_ms) VALUES ($1,$2,$3,$4,$5)",
                trade_id, account_id, qty, price, ts_ms
            )
            await tr.commit()
            return True
        except Exception as e:
            DB_ERRORS_TOTAL.inc()
            await tr.rollback()
            raise e
