from flask import Flask, request, jsonify
import time
import uuid
import os
import threading
import json
from hsm_client import sign_payload

app = Flask(__name__)

# 간단한 in-memory withdraw queue + idempotency store (데모용)
withdraw_queue = []
idempotency = set()
lock = threading.Lock()

@app.route("/withdraw", methods=["POST"])
def withdraw():
    """
    Body: { "user_id": <int>, "amount": <float>, "currency": "BTC", "idempotency_key": "<str>" }
    Response: { "status": "queued", "queue_time_s": <float>, "withdraw_id": "<uuid>" }
    """
    start = time.time()
    payload = request.get_json() or {}
    ik = payload.get("idempotency_key") or request.headers.get("Idempotency-Key")
    if not ik:
        return jsonify({"error": "idempotency_key required"}), 400

    with lock:
        if ik in idempotency:
            return jsonify({"status": "duplicate", "idempotency_key": ik}), 200
        idempotency.add(ik)
        wid = str(uuid.uuid4())
        sign_result = sign_payload(json.dumps({"wid":  
        withdraw_queue.append({
            "withdraw_id": wid,
            "user_id": payload.get("user_id"),
            "amount": payload.get("amount"),
            "currency": payload.get("currency", "BTC"),
            "created_at": time.time()
    
        })

    # mock queue processing time (non-blocking)
    queue_time = float(os.getenv("MOCK_QUEUE_TIME_S", "0.5"))
    return jsonify({"status": "queued", "queue_time_s": queue_time, "withdraw_id": wid}), 202

@app.route("/healthz")
def healthz():
    return "ok", 200

@app.route("/metrics")
def metrics():
    # 실 환경은 prometheus client 사용. 데모는 빈 응답
    return "", 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8081"))
    app.run(host="0.0.0.0", port=port)
