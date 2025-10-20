import os, json
from confluent_kafka import Producer

conf = {
    "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP", "kafka.data-platform.svc.cluster.local:9092"),
    "security.protocol": os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
    "sasl.username": os.getenv("KAFKA_SASL_USERNAME", "sophielog"),
    "sasl.password": os.getenv("KAFKA_SASL_PASSWORD", "sophielog"),
    "sasl.mechanisms": os.getenv("KAFKA_SASL_MECHANISMS", "PLAIN"),
    "client.id": "wallet-service",
}
producer = Producer(conf)
TOPIC = os.getenv("KAFKA_TOPIC", "wallet-withdraw")

def enqueue_withdraw(msg: dict):
    producer.produce(TOPIC, json.dumps(msg).encode("utf-8"))
    producer.poll(0)
