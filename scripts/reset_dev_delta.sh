#!/usr/bin/env bash
set -euo pipefail

ENV="${ENV:-dev}"
ROOT="data/${ENV}"

echo "⚠️  VAS A BORRAR TODO EN ${ROOT} (bronze/silver/gold/quarantine/checkpoints)"
read -rp "¿Continuar? (yes/no): " go
[[ "${go}" == "yes" ]] || { echo "Abortado"; exit 0; }

echo "🧹 Borrando capas y checkpoints de ${ROOT} ..."
rm -rf "${ROOT}/bronze/transactions"             || true
rm -rf "${ROOT}/silver/transactions"             || true
rm -rf "${ROOT}/gold/aggregates_daily"           || true
rm -rf "${ROOT}/gold/top_users_daily"            || true
rm -rf "${ROOT}/quarantine/transactions"         || true

rm -rf "${ROOT}/checkpoints/transactions_bronze" || true
rm -rf "${ROOT}/checkpoints/transactions_silver" || true
rm -rf "${ROOT}/checkpoints/transactions_gold"   || true

# (opcional) limpiar métricas si las tuvieras
rm -rf "${ROOT}/monitoring"                      || true

echo "✅ Limpieza de archivos OK."

echo "📁 Estructura resultante:"
mkdir -p "${ROOT}/bronze/transactions" \
         "${ROOT}/silver/transactions" \
         "${ROOT}/gold/aggregates_daily" \
         "${ROOT}/gold/top_users_daily" \
         "${ROOT}/quarantine/transactions" \
         "${ROOT}/checkpoints/transactions_bronze" \
         "${ROOT}/checkpoints/transactions_silver" \
         "${ROOT}/checkpoints/transactions_gold"

tree -L 3 "${ROOT}" 2>/dev/null || find "${ROOT}" -maxdepth 3 -type d -print

echo "🟢 Listo. DEV quedó limpio."
