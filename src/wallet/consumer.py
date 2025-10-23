import asyncio, json, os, time
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from .config import Config
from .metrics import PROCESSED_TOTAL, IDEMPOTENT_TOTAL, KAFKA_ERRORS_TOTAL, BAL_UPDATE_LAT, BATCH_LAT_MS, BATCH_SIZE
from .db import apply_trade

async def run_consumer():
    consumer = AIOKafkaConsumer(
        Config.TRADES_TOPIC,
        bootstrap_servers=Config.KAFKA_BROKERS,
        group_id=Config.GROUP_ID,
        enable_auto_commit=False,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        # (필요 시) security_protocol, sasl_mechanism, sasl_plain_username/password 추가
    )
    producer = AIOKafkaProducer(
        bootstrap_servers=Config.KAFKA_BROKERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    await consumer.start()
    await producer.start()
    try:
        batch, refs = [], []
        win_end = time.time() + (Config.BATCH_WINDOW_MS / 1000.0)
        while True:
            try:
                msg = await consumer.getone()
            except Exception as e:
                KAFKA_ERRORS_TOTAL.inc()
                await asyncio.sleep(0.1)
                continue

            batch.append(msg.value)
            refs.append(msg)
            if len(batch) >= Config.BATCH_SIZE or time.time() > win_end:
                if not batch:
                    win_end = time.time() + (Config.BATCH_WINDOW_MS / 1000.0)
                    continue

                BATCH_SIZE.observe(len(batch))
                t0 = time.time()
                # 순차 처리(데모) — 실무는 계정 단위 파티셔닝/병렬 워커
                for tr in batch:
                    t1 = time.time()
                    ok = await apply_trade(tr)
                    lat_ms = (time.time() - t1) * 1000.0
                    BAL_UPDATE_LAT.observe(lat_ms)
                    if ok:
                        PROCESSED_TOTAL.labels(result="applied").inc()
                        # downstream 통지 (wallet.tx)
                        await producer.send_and_wait(
                            Config.WALLET_TOPIC, {"trade_id": tr["trade_id"], "status": "applied", "ts": int(time.time()*1000)}
                        )
                    else:
                        PROCESSED_TOTAL.labels(result="idempotent").inc()
                        IDEMPOTENT_TOTAL.inc()
                BATCH_LAT_MS.observe((time.time() - t0) * 1000.0)
                await consumer.commit()
                batch, refs = [], []
                win_end = time.time() + (Config.BATCH_WINDOW_MS / 1000.0)
    finally:
        await consumer.stop()
        await producer.stop()
