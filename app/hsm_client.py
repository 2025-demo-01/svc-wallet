import os, requests
HSM_ENDPOINT = os.getenv("HSM_ENDPOINT", "http://hsm-mock.wallet.svc.cluster.local:9000")

def sign_payload(payload: str) -> dict:
    try:
        r = requests.post(f"{HSM_ENDPOINT}/sign", json={"payload": payload}, timeout=1.5)
        return r.json()
    except Exception:
        return {"status": "error"}
