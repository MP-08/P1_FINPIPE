# 🚀 FinPipe — Data Engineering Pipeline

> **FinPipe** es un proyecto de **Data Engineering end-to-end**, diseñado para simular el flujo completo de datos financieros en tiempo real.  
> Implementa una arquitectura **medallion (Bronze → Silver → Gold)** utilizando **Apache Kafka**, **Apache Spark Structured Streaming** y **Delta Lake**.

---

## 🧠 Objetivo del proyecto

El propósito de FinPipe es construir un pipeline de datos escalable y modular que permita:
- Ingestar transacciones financieras en tiempo real.
- Procesar, validar y limpiar datos con Spark.
- Persistir datos en formato **Delta Lake**.
- Generar **tablas analíticas (Gold)** con agregaciones y rankings de usuarios.

Este pipeline emula el trabajo diario de un **Data Engineer** en un entorno productivo.

---

## 🗺️ Roadmap del Proyecto

### 🔄 Relación entre los dos roadmaps: infraestructura + pipeline técnico

| Tipo de Roadmap | Etapa | Descripción real | Estado actual |
|-----------------|--------|------------------|---------------|
| 🧱 **Infraestructura (publicado)** | **Etapa 1 – On-Premise / Local** | Construcción del entorno local distribuido (Docker, Linux, Kafka, Spark, Delta Lake). Incluye el desarrollo del pipeline y su maduración (Bronze → Silver → Gold). | ✅ En curso |
| | **Etapa 2 – Orquestador (Airflow)** | Integración de **Apache Airflow** para controlar dependencias y programar los jobs Spark/Kafka. | 🔜 Próximo hito |
| | **Etapa 3 – Cloud-Native** | Migración del stack a servicios administrados (**AWS S3 / GCS / Dataproc / MSK**, etc.) con infraestructura como código. | ⏳ Futuro |
| ⚙️ **Pipeline técnico (actual)** | **Etapa 1a – Ingesta (Kafka → Bronze)** | Streaming de transacciones y almacenamiento crudo en Delta Lake. | ✅ |
| | **Etapa 1b – Transformación (Bronze → Silver)** | Limpieza, parseo y validación de datos. | ✅ |
| | **Etapa 1c – Curación (Silver → Gold)** | Agregaciones, KPIs y datos listos para analítica. | ✅ (etapa actual) |

---

## 🏗️ Arquitectura general


Cada capa cumple una función clara:
| Capa | Rol principal |
|------|----------------|
| **Bronze** | Ingesta cruda desde Kafka (eventos transaccionales). |
| **Silver** | Normalización, limpieza y validación de calidad de datos. |
| **Gold** | Agregaciones diarias y ranking de usuarios por volumen. |

---

## ⚙️ Stack tecnológico

| Componente | Descripción |
|-------------|-------------|
| 🐍 **Python 3.10+** | Lenguaje principal. |
| ☕ **Apache Spark 3.5.1** | Motor de procesamiento distribuido. |
| 🧱 **Delta Lake 3.2.0** | Formato transaccional ACID sobre archivos parquet. |
| 🔄 **Apache Kafka** | Ingesta de datos en tiempo real. |
| 🐳 **Docker Compose** | Orquestación local de servicios. |
| 🧰 **Makefile** | Automatización de comandos y flujos. |

---

## 📂 Estructura del proyecto


P1_FINPIPE/
├── jobs/
│ ├── streaming_to_bronze.py
│ ├── bronze_to_silver.py
│ └── silver_to_gold.py
├── kafka/
│ ├── producer.py
│ └── test_consumer.py
├── scripts/
│ ├── reset_dev_delta.sh
│ └── ...
├── docker/
│ └── docker-compose.yml
├── data/
│ └── dev/ (datasets locales, excluidos del repo)
├── logs/
│ └── dev/ (salidas de logs)
├── Makefile
├── requirements.txt
└── README.md

---

## 🧩 Flujo de ejecución (modo manual)

Cada etapa se ejecuta en una terminal separada 👇

```bash
# 1️⃣ Iniciar Kafka y Zookeeper
make start-docker

# 2️⃣ Iniciar el stream Kafka → Bronze
make stream-bronze

# 3️⃣ Iniciar el stream Bronze → Silver (Delta)
make bronze-to-silver

# 4️⃣ Iniciar el stream Silver → Gold (Delta)
make silver-to-gold

# 5️⃣ Largar el productor de transacciones falsas
make run-producer

---

## 🧩 Flujo de ejecución (modo manual)

Cada etapa se ejecuta en una terminal separada 👇

```bash
# 1️⃣ Iniciar Kafka y Zookeeper
make start-docker

# 2️⃣ Iniciar el stream Kafka → Bronze
make stream-bronze

# 3️⃣ Iniciar el stream Bronze → Silver (Delta)
make bronze-to-silver

# 4️⃣ Iniciar el stream Silver → Gold (Delta)
make silver-to-gold

# 5️⃣ Largar el productor de transacciones falsas
make run-producer

💡 Todos los logs se guardan automáticamente en:

logs/dev/
 ├── producer.log
 ├── bronze.log
 ├── silver.log
 └── gold.log

---

⚙️ Flujo automático (modo tmux)

Si tenés instalado tmux, podés correr todo el pipeline en una sola terminal:

make tmux-up

Esto crea una sesión con 4 paneles:

Producer

Kafka → Bronze

Bronze → Silver

Silver → Gold

Para salir sin detener nada:

Ctrl + b  luego  d

Y para volver:

tmux attach -t finpipe

---

🧹 Limpieza y mantenimiento

Reiniciar entorno de desarrollo:

make reset

Borrar logs antiguos:

make clean-logs

Apagar todo:

make kill-all

---

🧠 Conceptos clave aplicados

✅ Kafka Topics → transmisión de eventos financieros simulados.
✅ Spark Structured Streaming → lectura en tiempo real con tolerancia a fallas.
✅ Delta Lake → formato ACID con control de versiones y schema evolution.
✅ Data Validation Layer → separación automática de datos válidos y rechazados.
✅ Watermarks & Deduplication → manejo de eventos duplicados o tardíos.
✅ Aggregation Layer → tablas Gold con métricas por fecha, usuario y moneda.
✅ Makefile Orchestration → ejecución reproducible y controlada del pipeline.

---

🌐 Configuración de entornos

El pipeline soporta múltiples entornos:

ENV=dev   # por defecto
ENV=prod  # para entorno productivo simulado

Ejemplo:

ENV=prod make bronze-to-silver

Los datos se escribirán en data/prod/....

---

📈 Próximos pasos

🚀 Etapa 2 – Orquestador: integración con Apache Airflow o Prefect.
📦 Etapa 3 – Cloud Deployment: migración a AWS (S3 + MSK + EMR) o GCP (GCS + Dataproc + Pub/Sub).
📊 Etapa 4 – Visualización: análisis y dashboards con Tableau / Power BI / Streamlit.

---

👨‍💻 Autor

Matías Ezequiel Padilla Presas
📍 Data Engineer | Python, SQL, Spark | Data Pipelines & Cloud | Arquitecto BIM
🔗 linkedin.com/in/matias-padilla-presas

📦 github.com/MP-08

---

🧠 "FinPipe fue desarrollado con enfoque en la calidad de datos, escalabilidad y buenas prácticas de ingeniería, replicando un entorno productivo real."