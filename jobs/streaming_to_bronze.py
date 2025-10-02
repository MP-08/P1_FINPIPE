import os
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp, to_date
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

# ==========================
# Variables de entorno (DEV/PROD)
# ==========================
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "transactions_dev")
STARTING_OFFSETS = os.getenv("STARTING_OFFSETS", "earliest")  # <- unificamos nombre

OUTPUT_PATH = os.getenv("BRONZE_OUTPUT_PATH", "data/dev/bronze/transactions")
CHECKPOINT_PATH = os.getenv("BRONZE_CHECKPOINT_PATH", "data/dev/checkpoints/transactions_bronze")
PARTITION_COL = os.getenv("BRONZE_PARTITION_COL", "event_date")
APP_NAME = os.getenv("SPARK_APP_NAME", "finpipe_bronze_dev")

# ==========================
# Paths
# ==========================
Path(OUTPUT_PATH).mkdir(parents=True, exist_ok=True)
Path(CHECKPOINT_PATH).mkdir(parents=True, exist_ok=True)

# ==========================
# Esquema esperado del JSON
# ==========================
transaction_schema = StructType([
    StructField("transaction_id", StringType(), True),
    StructField("user_id", StringType(), True),
    StructField("amount", DoubleType(), True),
    StructField("currency", StringType(), True),
    StructField("timestamp", StringType(), True),  # llega como string ISO8601
])

# ==========================
# Spark Session
# ==========================
spark = (
    SparkSession.builder
    .appName(APP_NAME)
    .config("spark.jars.packages",
            "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,"
            "org.apache.kafka:kafka-clients:3.7.0")
    .config("spark.sql.streaming.schemaInference", "true")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

# ==========================
# Lectura de Kafka
# ==========================
print(f"📡 Conectando a Kafka en {KAFKA_BOOTSTRAP}, tópico={KAFKA_TOPIC}, offsets={STARTING_OFFSETS}")

df_raw = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
    .option("subscribe", KAFKA_TOPIC)
    .option("startingOffsets", STARTING_OFFSETS)
    .option("failOnDataLoss", "false")
    .load()
)

# ==========================
# Parseo de JSON desde Kafka
# ==========================
df_parsed = (
    df_raw
    .selectExpr("CAST(value AS STRING) as json_value")
    .select(from_json(col("json_value"), transaction_schema).alias("data"))
    .select("data.*")
    .withColumn("event_ts", to_timestamp(col("timestamp")))
    .withColumn("event_date", to_date(col("event_ts")))
)

# ==========================
# Escritura en Bronze (Parquet)
# ==========================
query = (
    df_parsed.writeStream
    .format("parquet")
    .option("path", OUTPUT_PATH)
    .option("checkpointLocation", CHECKPOINT_PATH)
    .partitionBy(PARTITION_COL)       # <- ahora usa env: event_date
    .outputMode("append")
    .start()
)

print(f"💾 Guardando transacciones en {OUTPUT_PATH} (checkpoint: {CHECKPOINT_PATH})")
query.awaitTermination()
