import os
import sys
import signal
import time
import json
import random
from datetime import datetime
from faker import Faker
from confluent_kafka import Producer

TOPIC = os.getenv("KAFKA_TOPIC", "transactions_dev")  # default dev
BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094")
SEC_PROTO = os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")

fake = Faker()
running = True

def handle_sigint(signum, frame):
    global running
    running = False
    print("\n[CANCELADO] Cortando producer...")

signal.signal(signal.SIGINT, handle_sigint)
signal.signal(signal.SIGTERM, handle_sigint)

def delivery_report(err, msg):
    if err is not None:
        print(f"[ERROR] Entrega fallida: {err}")
    else:
        print(f"[OK] {msg.topic()} [{msg.partition()}] offset {msg.offset()}")

def make_event():
    return {
        "transaction_id": fake.uuid4(),
        "user_id": random.randint(1000, 9999),
        "amount": round(random.uniform(5.0, 5000.0), 2),
        "currency": "USD",
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        # opcional: si quisieras que venga del productor para particionar sin derivarlo
        # "event_date": datetime.utcnow().date().isoformat(),
    }

def main():
    conf = {
        "bootstrap.servers": BOOTSTRAP,
        "security.protocol": SEC_PROTO,
        "linger.ms": 50
    }
    producer = Producer(conf)
    print(f"Produciendo en topic '{TOPIC}' → {BOOTSTRAP} (Ctrl+C para salir)")

    try:
        while running:
            ev = make_event()
            producer.produce(TOPIC, json.dumps(ev), callback=delivery_report)
            producer.poll(0)
            time.sleep(0.3)
    finally:
        print("\nVaciando buffer...")
        producer.flush(10)
        print("Producer cerrado.")

if __name__ == "__main__":
    main()
