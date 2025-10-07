# ========= Config =========
ENV ?= dev
TOPIC ?= transactions

SPARK_SUBMIT = spark-submit
COMPOSE = docker compose -f docker/docker-compose.yml

# Paquetes
DELTA_PKG = io.delta:delta-spark_2.12:3.2.0
KAFKA_PKG = org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1
DELTA_CONF = --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
             --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog

# Paths por ENV
DATA_ROOT = data/$(ENV)
BRONZE_OUT = $(DATA_ROOT)/bronze/transactions
BRONZE_CKP = $(DATA_ROOT)/checkpoints/transactions_bronze
SILVER_OUT = $(DATA_ROOT)/silver/transactions
SILVER_CKP = $(DATA_ROOT)/checkpoints/transactions_silver
GOLD_CKP   = $(DATA_ROOT)/checkpoints/transactions_gold
QUARANTINE_OUT = $(DATA_ROOT)/quarantine/transactions

.PHONY: help start-docker stop-docker recreate-topic reset-dev \
        run-producer stream-bronze bronze-to-silver silver-to-gold \
        tmux-up kill-all

help:
	@echo "Targets útiles:"
	@echo "  make start-docker      # Levanta ZooKeeper/Kafka del compose"
	@echo "  make stop-docker       # Baja el stack de docker"
	@echo "  make recreate-topic    # Borra y crea el topic ($(TOPIC))"
	@echo "  make reset-dev         # Limpia data y checkpoints de $(ENV)"
	@echo "  make stream-bronze     # Kafka -> Bronze (Parquet)"
	@echo "  make bronze-to-silver  # Bronze -> Silver (Delta)"
	@echo "  make silver-to-gold    # Silver -> Gold (Delta)"
	@echo "  make run-producer      # Lanza el generador de eventos"
	@echo "  make tmux-up           # (Opcional) Levanta todo en una sola consola con tmux"
	@echo "  make kill-all          # Mata spark-submit y producer"

# ----- Infra -----
start-docker:
	$(COMPOSE) up -d

stop-docker:
	$(COMPOSE) down

recreate-topic:
	$(COMPOSE) exec kafka bash -lc "/usr/bin/kafka-topics --bootstrap-server localhost:9092 --delete --topic $(TOPIC) || true"
	$(COMPOSE) exec kafka bash -lc "/usr/bin/kafka-topics --bootstrap-server localhost:9092 --create --topic $(TOPIC) --partitions 1 --replication-factor 1 --if-not-exists"
	$(COMPOSE) exec kafka bash -lc "/usr/bin/kafka-topics --bootstrap-server localhost:9092 --list"

reset-dev:
	@ENV=$(ENV) ./scripts/reset_dev_delta.sh

# ----- Procesos streaming (abrí 4 consolas y corré cada target) -----
run-producer:
	python kafka/producer.py

stream-bronze:
	ENV=$(ENV) BRONZE_OUTPUT_PATH=$(BRONZE_OUT) BRONZE_CHECKPOINT_PATH=$(BRONZE_CKP) \
	$(SPARK_SUBMIT) --packages $(KAFKA_PKG) jobs/streaming_to_bronze.py

bronze-to-silver:
	ENV=$(ENV) SILVER_OUTPUT_PATH=$(SILVER_OUT) QUARANTINE_OUTPUT_PATH=$(QUARANTINE_OUT) SILVER_CHECKPOINT_PATH=$(SILVER_CKP) \
	$(SPARK_SUBMIT) --packages $(DELTA_PKG) $(DELTA_CONF) jobs/bronze_to_silver.py

silver-to-gold:
	ENV=$(ENV) SILVER_OUTPUT_PATH=$(SILVER_OUT) GOLD_CHECKPOINT_PATH=$(GOLD_CKP) \
	$(SPARK_SUBMIT) --packages $(DELTA_PKG) $(DELTA_CONF) jobs/silver_to_gold.py

# ----- (Opcional) levantar todo con tmux en una consola -----
tmux-up:
	@tmux new-session -d -s finpipe "make start-docker; sleep 2; make stream-bronze"
	@tmux split-window -v -t finpipe "make bronze-to-silver"
	@tmux split-window -h -t finpipe "make silver-to-gold"
	@tmux select-pane -t 0
	@tmux split-window -h -t finpipe "make run-producer"
	@tmux select-layout -t finpipe tiled
	@tmux attach -t finpipe

# ----- Utilidades -----
kill-all:
	- pkill -f "spark-submit" || true
	- pkill -f "producer.py" || true
