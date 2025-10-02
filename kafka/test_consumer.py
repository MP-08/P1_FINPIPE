import os
import json
import sys
import signal
from confluent_kafka import Consumer, KafkaException

TOPIC = os.getenv("KAFKA_TOPIC", "transactions")
BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "debug-consumer")

running = True
def handle_sigint(signum, frame):
    global running
    running = False
signal.signal(signal.SIGINT, handle_sigint)
signal.signal(signal.SIGTERM, handle_sigint)

def main():
    conf = {
        "bootstrap.servers": BOOTSTRAP,
        "group.id": GROUP_ID,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    }
    consumer = Consumer(conf)
    consumer.subscribe([TOPIC])

    print(f"Escuchando '{TOPIC}' en {BOOTSTRAP} (Ctrl+C para salir)")
    try:
        while running:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                raise KafkaException(msg.error())
            try:
                data = json.loads(msg.value().decode("utf-8"))
            except Exception:
                data = msg.value().decode("utf-8")
            print(data)
    finally:
        consumer.close()
        print("Consumer cerrado.")

if __name__ == "__main__":
    main()
