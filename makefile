# ========= CONFIGURACIÓN GLOBAL =========
ENV ?= dev
TOPIC ?= transactions

SPARK_SUBMIT = spark-submit
COMPOSE = docker compose -f docker/docker-compose.yml
LOG_DIR = logs/$(ENV)

DELTA_PKG = io.delta:delta-spark_2.12:3.2.0
KAFKA_PKG = org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1
DELTA_CONF = --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
             --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog

DATA_ROOT = data/$(ENV)
BRONZE_OUT = $(DATA_ROOT)/bronze/transactions
BRONZE_CKP = $(DATA_ROOT)/checkpoints/transactions_bronze
SILVER_OUT = $(DATA_ROOT)/silver/transactions
SILVER_CKP = $(DATA_ROOT)/checkpoints/transactions_silver
GOLD_CKP   = $(DATA_ROOT)/checkpoints/transactions_gold
QUARANTINE_OUT = $(DATA_ROOT)/quarantine/transactions

.PHONY: help start-docker stop-docker recreate-topic reset clean-logs \
        run-producer stream-bronze bronze-to-silver silver-to-gold \
        tmux-up kill-all

# ========= AYUDA =========
help:
	@echo "🔧 Comandos disponibles:"
	@echo ""
	@echo "Infraestructura:"
	@echo "  make start-docker       -> Levanta Kafka y Zookeeper"
	@echo "  make stop-docker        -> Baja los contenedores"
	@echo "  make recreate-topic     -> Borra y crea el topic '$(TOPIC)' limpio"
	@echo ""
	@echo "Ambiente y limpieza:"
	@echo "  make reset              -> Limpia datos y checkpoints del entorno $(ENV)"
	@echo "  make clean-logs         -> Limpia logs del entorno $(ENV)"
	@echo ""
	@echo "Streaming jobs (abrir en consolas separadas):"
	@echo "  make run-producer       -> Lanza el generador de transacciones falsas"
	@echo "  make stream-bronze      -> Kafka → Bronze"
	@echo "  make bronze-to-silver   -> Bronze → Silver (Delta)"
	@echo "  make silver-to-gold     -> Silver → Gold (Delta)"
	@echo ""
	@echo "Modo orquestado:"
	@echo "  make tmux-up            -> Levanta todo en una sola consola con tmux"
	@echo "  make kill-all           -> Detiene todos los procesos Spark y el producer"
	@echo ""
	@echo "Uso de entornos:"
	@echo "  ENV=dev make run-silver   (default)"
	@echo "  ENV=prod make run-silver  (usa rutas data/prod/...)"


# ========= INFRA =========
start-docker:
	$(COMPOSE) up -d

stop-docker:
	$(COMPOSE) down

recreate-topic:
	$(COMPOSE) exec kafka bash -lc "/usr/bin/kafka-topics --bootstrap-server localhost:9092 --delete --topic $(TOPIC) || true"
	$(COMPOSE) exec kafka bash -lc "/usr/bin/kafka-topics --bootstrap-server localhost:9092 --create --topic $(TOPIC) --partitions 1 --replication-factor 1 --if-not-exists"
	$(COMPOSE) exec kafka bash -lc "/usr/bin/kafka-topics --bootstrap-server localhost:9092 --list"

# ========= MANTENIMIENTO =========
reset:
	@ENV=$(ENV) ./scripts/reset_dev_delta.sh

clean-logs:
	rm -rf $(LOG_DIR) && mkdir -p $(LOG_DIR)
	@echo "🧹 Logs del entorno $(ENV) eliminados."


# ========= STREAMING PROCESOS =========
run-producer:
	mkdir -p $(LOG_DIR)
	python kafka/producer.py | tee $(LOG_DIR)/producer.log

stream-bronze:
	mkdir -p $(LOG_DIR)
	ENV=$(ENV) $(SPARK_SUBMIT) \
		--packages $(KAFKA_PKG) jobs/streaming_to_bronze.py | tee $(LOG_DIR)/bronze.log

bronze-to-silver:
	mkdir -p $(LOG_DIR)
	ENV=$(ENV) $(SPARK_SUBMIT) \
		--packages $(DELTA_PKG) $(DELTA_CONF) jobs/bronze_to_silver.py | tee $(LOG_DIR)/silver.log

silver-to-gold:
	mkdir -p $(LOG_DIR)
	ENV=$(ENV) $(SPARK_SUBMIT) \
		--packages $(DELTA_PKG) $(DELTA_CONF) jobs/silver_to_gold.py | tee $(LOG_DIR)/gold.log


# ========= MODO ORQUESTADO (opcional con tmux) =========
tmux-up:
	@tmux new-session -d -s finpipe "make start-docker; sleep 3; make stream-bronze"
	@tmux split-window -v -t finpipe "make bronze-to-silver"
	@tmux split-window -h -t finpipe "make silver-to-gold"
	@tmux select-pane -t 0
	@tmux split-window -h -t finpipe "make run-producer"
	@tmux select-layout -t finpipe tiled
	@tmux attach -t finpipe

kill-all:
	- pkill -f "spark-submit" || true
	- pkill -f "producer.py" || true

