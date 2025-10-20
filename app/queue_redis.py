import os, json, redis
_redis = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis.wallet.svc.cluster.local"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    password=os.getenv("REDIS_PASSWORD", "sophielog"),
    db=0, decode_responses=True,
)

QUEUE_KEY = os.getenv("REDIS_QUEUE_KEY", "wallet:withdraw:queue")

def enqueue_withdraw(msg: dict):
    _redis.lpush(QUEUE_KEY, json.dumps(msg))
