import os
from pathlib import Path
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, sum as _sum, count as _count, avg as _avg,
    desc, dense_rank
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, TimestampType, DateType
)
from pyspark.sql.window import Window

ENV = os.getenv("ENV", "dev")
DATA_ROOT = os.getenv("DATA_ROOT", f"data/{ENV}")

SILVER_PATH       = os.getenv("SILVER_OUTPUT_PATH",    f"{DATA_ROOT}/silver/transactions")
GOLD_ROOT         = os.getenv("GOLD_OUTPUT_PATH",      f"{DATA_ROOT}/gold")
CHECKPOINT_GOLD   = os.getenv("GOLD_CHECKPOINT_PATH",  f"{DATA_ROOT}/checkpoints/transactions_gold")

AGG_DAILY_PATH       = os.path.join(GOLD_ROOT, "aggregates_daily")
TOP_USERS_DAILY_PATH = os.path.join(GOLD_ROOT, "top_users_daily")

for p in [AGG_DAILY_PATH, TOP_USERS_DAILY_PATH, CHECKPOINT_GOLD]:
    Path(p).mkdir(parents=True, exist_ok=True)

silver_schema = StructType([
    StructField("transaction_id", StringType(), True),
    StructField("user_id",        StringType(), True),
    StructField("amount",         DoubleType(), True),
    StructField("currency",       StringType(), True),
    StructField("timestamp",      StringType(), True),
    StructField("event_ts_utc",   TimestampType(), True),
    StructField("event_date",     DateType(), True)
])

def build_aggregates_daily(df: DataFrame) -> DataFrame:
    return (
        df.groupBy("event_date", "currency")
          .agg(
              _sum("amount").alias("total_amount"),
              _count("*").alias("tx_count"),
              _avg("amount").alias("avg_amount"),
              _count("user_id").alias("unique_users")
          )
    )

def write_aggregates_daily(batch_df: DataFrame, batch_id: int):
    if batch_df.rdd.isEmpty():
        return
    agg = build_aggregates_daily(batch_df)
    (agg.write
        .format("delta")     # 👈 Parquet → Delta
        .mode("append")
        .partitionBy("event_date")
        .save(AGG_DAILY_PATH))

def write_top_users_daily(batch_df: DataFrame, batch_id: int):
    if batch_df.rdd.isEmpty():
        return
    per_user = (
        batch_df.groupBy("event_date", "currency", "user_id")
                .agg(
                    _sum("amount").alias("amount_sum"),
                    _count("*").alias("tx_count")
                )
    )
    w = Window.partitionBy("event_date", "currency").orderBy(desc("amount_sum"))
    ranked = per_user.withColumn("rank", dense_rank().over(w)).filter(col("rank") <= 10)

    (ranked.write
        .format("delta")     # 👈 Parquet → Delta
        .mode("append")
        .partitionBy("event_date")
        .save(TOP_USERS_DAILY_PATH))

if __name__ == "__main__":
    spark = SparkSession.builder.appName("FinPipe Silver->Gold (Delta)").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")

    print(f"[CONFIG] ENV={ENV}")
    print(f"[CONFIG] SILVER_PATH={SILVER_PATH}")
    print(f"[CONFIG] GOLD_ROOT={GOLD_ROOT}")
    print(f"[CONFIG] CHECKPOINT_GOLD={CHECKPOINT_GOLD}")

    silver_stream = (
        spark.readStream
             .schema(silver_schema)
             .format("delta")   # 👈 Parquet → Delta
             .load(SILVER_PATH)
    )
    silver_wm = silver_stream.withWatermark("event_ts_utc", "2 hours")

    q_agg = (
        silver_wm.writeStream
                 .foreachBatch(write_aggregates_daily)
                 .option("checkpointLocation", os.path.join(CHECKPOINT_GOLD, "aggregates_daily"))
                 .outputMode("update")
                 .start()
    )

    q_top = (
        silver_wm.writeStream
                 .foreachBatch(write_top_users_daily)
                 .option("checkpointLocation", os.path.join(CHECKPOINT_GOLD, "top_users_daily"))
                 .outputMode("update")
                 .start()
    )

    spark.streams.awaitAnyTermination()
