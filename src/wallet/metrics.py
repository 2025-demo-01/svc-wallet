from prometheus_client import Counter, Histogram

BAL_UPDATE_LAT = Histogram("wallet_balance_update_latency_ms",
                           "Latency for processing a trade to balance update (ms)",
                           buckets=(5,10,20,30,50,80,120,200,500,1000))
PROCESSED_TOTAL = Counter("wallet_processed_total", "Total processed trades", ["result"])
IDEMPOTENT_TOTAL = Counter("wallet_idempotent_total", "Idempotent hits")
DB_ERRORS_TOTAL = Counter("wallet_db_errors_total", "DB errors")
KAFKA_ERRORS_TOTAL = Counter("wallet_kafka_errors_total", "Kafka errors")
BATCH_LAT_MS = Histogram("wallet_batch_latency_ms", "Batch processing latency (ms)")
BATCH_SIZE = Histogram("wallet_batch_size", "Current batch size", buckets=(1,5,10,20,50,100,200,500,1000))
