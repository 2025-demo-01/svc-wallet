import time, json
def now_ms() -> int: return int(time.time() * 1000)
def j(v) -> str: return json.dumps(v, separators=(",", ":"))
