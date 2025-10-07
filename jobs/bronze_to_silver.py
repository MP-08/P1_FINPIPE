import os
from pathlib import Path
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, lit, to_timestamp, to_utc_timestamp, to_date,
    when, expr, to_json, struct, upper, trim
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, TimestampType
)

# =========================
# Entorno y paths por defecto (dev/prod)
# =========================
ENV = os.getenv("ENV", "dev")
DATA_ROOT = os.getenv("DATA_ROOT", f"data/{ENV}")

BRONZE_PATH        = os.getenv("BRONZE_OUTPUT_PATH",     f"{DATA_ROOT}/bronze/transactions")
SILVER_PATH        = os.getenv("SILVER_OUTPUT_PATH",     f"{DATA_ROOT}/silver/transactions")
QUARANTINE_PATH    = os.getenv("QUARANTINE_OUTPUT_PATH", f"{DATA_ROOT}/quarantine/transactions")
CHECKPOINT_ROOT    = os.getenv("SILVER_CHECKPOINT_PATH", f"{DATA_ROOT}/checkpoints/transactions_silver")
SOURCE_TZ          = os.getenv("SOURCE_TIMEZONE", "UTC")
ALLOWED_CURRENCIES = os.getenv("ALLOWED_CURRENCIES", "USD,ARS,EUR").split(",")

for p in [SILVER_PATH, QUARANTINE_PATH, CHECKPOINT_ROOT]:
    Path(p).mkdir(parents=True, exist_ok=True)

# =========================
# Esquema esperado en Bronze (Parquet)
# =========================
bronze_schema = StructType([
    StructField("transaction_id", StringType(), True),
    StructField("user_id",        StringType(), True),
    StructField("amount",         DoubleType(), True),
    StructField("currency",       StringType(), True),
    StructField("timestamp",      StringType(), True)
])

# =========================
# Transformación a Silver
# =========================
def transform_to_silver(df: DataFrame):
    df1 = (
        df
        .withColumn("transaction_id", trim(col("transaction_id")))
        .withColumn("user_id", trim(col("user_id")))
        .withColumn("currency", upper(trim(col("currency"))))
        .withColumn("event_ts_raw", to_timestamp(col("timestamp")))
    )

    df2 = df1.withColumn(
        "event_ts_utc",
        when(
            col("event_ts_raw").isNotNull(),
            to_utc_timestamp(col("event_ts_raw"), SOURCE_TZ)
        ).otherwise(lit(None).cast(TimestampType()))
    ).drop("event_ts_raw")

    allowed = [c.strip().upper() for c in ALLOWED_CURRENCIES if c.strip()]
    allowed_list = ", ".join([f"'{c}'" for c in allowed])

    df_rules = df2.withColumn(
        "validation_reason",
        expr(
            "CASE "
            "WHEN transaction_id IS NULL OR transaction_id = '' THEN 'MISSING_TRANSACTION_ID' "
            "WHEN user_id IS NULL OR user_id = '' THEN 'MISSING_USER_ID' "
            "WHEN amount IS NULL THEN 'AMOUNT_NULL' "
            "WHEN amount <= 0 THEN 'AMOUNT_NON_POSITIVE' "
            f"WHEN currency IS NULL OR currency = '' OR currency NOT IN ({allowed_list}) THEN 'CURRENCY_INVALID' "
            "WHEN event_ts_utc IS NULL THEN 'TIMESTAMP_INVALID' "
            "ELSE NULL END"
        )
    )

    valid_df = (
        df_rules
        .filter(col("validation_reason").isNull())
        .drop("validation_reason")
        .withColumn("event_date", to_date(col("event_ts_utc")))
    )

    quarantine_df = (
        df_rules
        .filter(col("validation_reason").isNotNull())
        .withColumn("raw_payload", to_json(struct([col(c) for c in df.columns])))
        .withColumn("event_date", to_date(to_timestamp(col("timestamp"))))
    )

    return valid_df, quarantine_df


if __name__ == "__main__":
    spark = SparkSession.builder.appName("FinPipe Bronze->Silver (Delta)").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    print(f"[CONFIG] ENV={ENV}")
    print(f"[CONFIG] BRONZE_PATH={BRONZE_PATH}")
    print(f"[CONFIG] SILVER_PATH={SILVER_PATH}")
    print(f"[CONFIG] QUARANTINE_PATH={QUARANTINE_PATH}")
    print(f"[CONFIG] CHECKPOINT_ROOT={CHECKPOINT_ROOT}")

    bronze_stream = (
        spark.readStream
        .schema(bronze_schema)
        .format("parquet")
        .load(BRONZE_PATH)
    )

    valid_silver_stream, quarantine_stream = transform_to_silver(bronze_stream)

    dedup_stream = (
        valid_silver_stream
        .withWatermark("event_ts_utc", "2 hours")
        .dropDuplicates(["transaction_id"])
    )

    # ✅ Escribir en formato Delta
    silver_writer = (
        dedup_stream
        .writeStream
        .format("delta")
        .option("path", SILVER_PATH)
        .option("checkpointLocation", os.path.join(CHECKPOINT_ROOT, "silver"))
        .partitionBy("event_date")
        .outputMode("append")
        .start()
    )

    quarantine_writer = (
        quarantine_stream
        .writeStream
        .format("delta")
        .option("path", QUARANTINE_PATH)
        .option("checkpointLocation", os.path.join(CHECKPOINT_ROOT, "quarantine"))
        .partitionBy("event_date")
        .outputMode("append")
        .start()
    )

    # Métricas (foreachBatch)
    def log_metrics(batch_df: DataFrame, batch_id: int):
        total = batch_df.count()
        print(f"[Silver Metrics] batch_id={batch_id} valid_rows={total}")

    def log_quarantine(batch_df: DataFrame, batch_id: int):
        total = batch_df.count()
        reasons = (batch_df.groupBy("validation_reason").count().collect()
                   if total > 0 else [])
        print(f"[Quarantine Metrics] batch_id={batch_id} rejected_rows={total} reasons={reasons}")

    (
        dedup_stream.writeStream
        .foreachBatch(lambda df, bid: log_metrics(df, bid))
        .option("checkpointLocation", os.path.join(CHECKPOINT_ROOT, "silver_metrics"))
        .outputMode("update")
        .start()
    )

    (
        quarantine_stream.writeStream
        .foreachBatch(lambda df, bid: log_quarantine(df, bid))
        .option("checkpointLocation", os.path.join(CHECKPOINT_ROOT, "quarantine_metrics"))
        .outputMode("update")
        .start()
    )

    spark.streams.awaitAnyTermination()
