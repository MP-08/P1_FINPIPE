from __future__ import annotations
from pathlib import Path
from pyspark.sql import SparkSession

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BRONZE_PATH = PROJECT_ROOT / "data" / "bronze" / "transactions"

spark = (
    SparkSession.builder
    .appName("CheckBronze")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

print(f"📂 Leyendo datos de: {BRONZE_PATH}")

df = spark.read.parquet(str(BRONZE_PATH))

print("\n=== Schema de Bronze ===")
df.printSchema()

print("\n=== Primeras filas ===")
df.show(10, truncate=False)

print("\n=== Métricas básicas ===")
print("Total de filas:", df.count())

print("\n=== Particiones encontradas ===")
cols = df.columns
part_col = "event_date" if "event_date" in cols else ("ingestion_date" if "ingestion_date" in cols else None)
if part_col:
    parts = [r[part_col] for r in df.select(part_col).distinct().orderBy(part_col).collect()]
    print(parts)
else:
    print("No se encontró columna de partición (event_date / ingestion_date).")

print("\n=== Archivos parquet detectados ===")
for p in BRONZE_PATH.rglob("*.parquet"):
    print(p)

spark.stop()
