import os

def env(k: str, d: str = "") -> str:
    return os.getenv(k, d)

class Config:
    KAFKA_BROKERS = env("KAFKA_BROKERS", "localhost:9092")
    TRADES_TOPIC  = env("TRADES_OUT_TOPIC", "trades.out")
    WALLET_TOPIC  = env("WALLET_TX_TOPIC", "wallet.tx")
    GROUP_ID      = env("KAFKA_GROUP_ID", "wallet-consumer")
    PG_DSN        = env("PG_DSN", "postgres://user:pass@aurora-postgres:5432/wallet")
    OTEL_ENDPOINT = env("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    APP_ENV       = env("APP_ENV", "dev")
    BATCH_SIZE    = int(env("BATCH_SIZE", "500"))
    BATCH_WINDOW_MS = int(env("BATCH_WINDOW_MS", "50"))
