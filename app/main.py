# svc-wallet/app/main.py
import os
import time
import uuid
import json
import threading
from typing import Dict, Any

from flask import Flask, request, jsonify

# Prometheus metrics (histogram/gauge/counter)
# requirements.txt에 prometheus_client가 없다면 추가해야 한다:
# prometheus_client==0.20.0
try:
    from prometheus_client import (
        Histogram, Gauge, Counter, generate_latest, CONTENT_TYPE_LATEST
    )
except Exception:  # 환경에 따라 임시 동작(지표 미노출)
    Histogram = Gauge = Counter = None
    def generate_latest():  # type: ignore
        return b""
    CONTENT_TYPE_LATEST = "text/plain"

# 선택적 큐 백엔드: memory / redis / kafka
QUEUE_BACKEND = os.getenv("QUEUE_BACKEND", "memory").strip().lower()

# Redis 구성 (선택)
REDIS_HOST = os.getenv("REDIS_HOST", "redis.wallet.svc.cluster.local")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "sophielog")
REDIS_QUEUE_KEY = os.getenv("REDIS_QUEUE_KEY", "wallet:withdraw:queue")

# Kafka 구성 (선택)
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka.data-platform.svc.cluster.local:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "wallet-withdraw")
KAFKA_SECURITY_PROTOCOL = os.getenv("KAFKA_SECURITY_PROTOCOL", "SASL_PLAINTEXT")
KAFKA_SASL_MECHANISMS = os.getenv("KAFKA_SASL_MECHANISMS", "PLAIN")
KAFKA_SASL_USERNAME = os.getenv("KAFKA_SASL_USERNAME", "sophielog")
KAFKA_SASL_PASSWORD = os.getenv("KAFKA_SASL_PASSWORD", "sophielog")

# 모의 처리 지연(초)
MOCK_QUEUE_TIME_S = float(os.getenv("MOCK_QUEUE_TIME_S", "0.5"))

# HSM/MPC 모의 서명 엔드포인트
HSM_ENDPOINT = os.getenv("HSM_ENDPOINT", "http://hsm-mock.wallet.svc.cluster.local:9000")

# 애플리케이션
app = Flask(__name__)

# In-memory 자료구조 (memory 백엔드용)
withdraw_queue = []
idempotency_local = set()
lock = threading.Lock()

# 백엔드 의존성 로딩
redis_client = None
if QUEUE_BACKEND == "redis":
    try:
        import redis  # type: ignore
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            db=0,
            decode_responses=True,
        )
    except Exception:
        redis_client = None

kafka_producer = None
if QUEUE_BACKEND == "kafka":
    try:
        from confluent_kafka import Producer  # type: ignore
        kafka_producer = Producer({
            "bootstrap.servers": KAFKA_BOOTSTRAP,
            "security.protocol": KAFKA_SECURITY_PROTOCOL,
            "sasl.mechanisms": KAFKA_SASL_MECHANISMS,
            "sasl.username": KAFKA_SASL_USERNAME,
            "sasl.password": KAFKA_SASL_PASSWORD,
            "client.id": "wallet-service",
        })
    except Exception:
        kafka_producer = None

# Prometheus 지표 정의
if Histogram is not None:
    # 관측 스택에서 사용: wallet_withdraw_queue_time_seconds_bucket 등
    WALLET_QUEUE_TIME = Histogram(
        "wallet_withdraw_queue_time_seconds",
        "Time from enqueue to acknowledgement for withdraw requests (simulated)",
        buckets=(0.05, 0.1, 0.2, 0.5, 1, 2, 5),
    )
    WALLET_QUEUE_DEPTH = Gauge(
        "wallet_withdraw_queue_depth",
        "Current pending withdraw queue depth (approx)"
    )
    WALLET_REQUESTS_TOTAL = Counter(
        "wallet_withdraw_requests_total",
        "Total withdraw requests"
    )
else:
    WALLET_QUEUE_TIME = WALLET_QUEUE_DEPTH = WALLET_REQUESTS_TOTAL = None


def observe_queue_time(seconds: float) -> None:
    if WALLET_QUEUE_TIME is not None:
        WALLET_QUEUE_TIME.observe(seconds)


def set_queue_depth(n: int) -> None:
    if WALLET_QUEUE_DEPTH is not None:
        WALLET_QUEUE_DEPTH.set(float(n))


def inc_requests() -> None:
    if WALLET_REQUESTS_TOTAL is not None:
        WALLET_REQUESTS_TOTAL.inc()


def hsm_sign(payload: Dict[str, Any]) -> Dict[str, Any]:
    """모의 HSM/MPC 서버 요청. 실패해도 서비스는 계속 진행."""
    try:
        import requests  # type: ignore
        r = requests.post(f"{HSM_ENDPOINT}/sign", json={"payload": json.dumps(payload)}, timeout=1.5)
        return r.json()
    except Exception:
        return {"status": "error"}


def enqueue_memory(msg: Dict[str, Any]) -> None:
    with lock:
        withdraw_queue.append(msg)
        set_queue_depth(len(withdraw_queue))


def enqueue_redis(msg: Dict[str, Any]) -> None:
    if not redis_client:
        enqueue_memory(msg)
        return
    redis_client.lpush(REDIS_QUEUE_KEY, json.dumps(msg))
    try:
        # 근사치: 리스트 길이 조회
        depth = int(redis_client.llen(REDIS_QUEUE_KEY))
        set_queue_depth(depth)
    except Exception:
        pass


def enqueue_kafka(msg: Dict[str, Any]) -> None:
    if not kafka_producer:
        enqueue_memory(msg)
        return
    kafka_producer.produce(KAFKA_TOPIC, json.dumps(msg).encode("utf-8"))
    kafka_producer.poll(0)
    # 큐 길이는 브로커 기준이므로 생략(지표는 소비자에서 측정)


def already_processed(idem_key: str) -> bool:
    """아이템포턴시 검증. redis를 쓰면 분산 세트로 처리."""
    if QUEUE_BACKEND == "redis" and redis_client:
        # 24시간 TTL 분산 키
        inserted = redis_client.set(f"idem:{idem_key}", "1", nx=True, ex=24 * 3600)
        return inserted is None
    else:
        with lock:
            if idem_key in idempotency_local:
                return True
            idempotency_local.add(idem_key)
            return False


@app.route("/withdraw", methods=["POST"])
def withdraw() -> Any:
    """
    Body: { "user_id": <int>, "amount": <float>, "currency": "BTC", "idempotency_key": "<str>" }
    Response: { "status": "queued", "queue_time_s": <float>, "withdraw_id": "<uuid>", "hsm_status": "<ok|error>" }
    """
    inc_requests()
    t0 = time.time()

    payload = request.get_json(silent=True) or {}
    idem_key = payload.get("idempotency_key") or request.headers.get("Idempotency-Key")
    if not idem_key:
        return jsonify({"error": "idempotency_key required"}), 400

    if already_processed(idem_key):
        observe_queue_time(0.0)
        return jsonify({"status": "duplicate", "idempotency_key": idem_key}), 200

    wid = str(uuid.uuid4())
    msg = {
        "withdraw_id": wid,
        "user_id": payload.get("user_id"),
        "amount": payload.get("amount"),
        "currency": payload.get("currency", "BTC"),
        "created_at": time.time(),
    }

    # 큐 백엔드에 적재
    if QUEUE_BACKEND == "redis":
        enqueue_redis(msg)
    elif QUEUE_BACKEND == "kafka":
        enqueue_kafka(msg)
    else:
        enqueue_memory(msg)

    # 모의 서명 호출(HSM/MPC)
    hsm_result = hsm_sign({"wid": wid, "amount": msg.get("amount"), "currency": msg.get("currency")})
    hsm_status = hsm_result.get("status", "ok")

    # 모의 큐 대기 시간 관측
    # 실제 운영에서는 큐 처리 완료까지의 end-to-end 지표를 별도 수집
    observe_queue_time(MOCK_QUEUE_TIME_S)

    # 응답
    elapsed = time.time() - t0
    return (
        jsonify({
            "status": "queued",
            "queue_time_s": MOCK_QUEUE_TIME_S,
            "elapsed_s": round(elapsed, 3),
            "withdraw_id": wid,
            "hsm_status": hsm_status
        }),
        202,
    )


@app.route("/healthz", methods=["GET"])
def healthz() -> Any:
    return "ok", 200


@app.route("/metrics", methods=["GET"])
def metrics() -> Any:
    data = generate_latest()
    return app.response_class(data, mimetype=CONTENT_TYPE_LATEST)


def _background_memory_consumer() -> None:
    """메모리 큐 사용 시 데모용 소비자(지표 업데이트 용도)."""
    while True:
        time.sleep(1.0)
        if QUEUE_BACKEND != "memory":
            time.sleep(4.0)
            continue
        with lock:
            # 간단한 소비
            if withdraw_queue:
                # 한 번에 몇 개 처리
                take = min(10, len(withdraw_queue))
                del withdraw_queue[:take]
                set_queue_depth(len(withdraw_queue))


if __name__ == "__main__":
    # 백그라운드 소비자(thread)는 데모용
    th = threading.Thread(target=_background_memory_consumer, daemon=True)
    th.start()

    port = int(os.getenv("PORT", "8081"))
    app.run(host="0.0.0.0", port=port)
