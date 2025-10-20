from flask import Flask, request, jsonify
app = Flask(__name__)

@app.post("/sign")
def sign():
    body = request.get_json() or {}
    payload = body.get("payload", "")
    return jsonify({"signature": f"sig-{hash(payload)%100000}", "status": "ok"})

@app.get("/healthz")
def health():
    return "ok", 200

if __name__ == "__main__":
    app.run("0.0.0.0", 9000)
