#!/bin/sh
# Prepara o MinIO: bucket, política e usuário da aplicação.
# É idempotente: pode rodar várias vezes sem quebrar nada.
# Origem: Guia Parte 4.5 / Aula 04
set -eu

echo "[init] aguardando o MinIO responder..."
until mc alias set local "http://minio:9000" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1; do
  sleep 2
done

echo "[init] criando bucket ${RAIS_BUCKET}"
mc mb --ignore-existing "local/${RAIS_BUCKET}"

echo "[init] criando política e usuário da aplicação"
mc admin policy create local rais-rw /init/policy-rais.json 2>/dev/null || true
mc admin user add local "$APP_ACCESS_KEY" "$APP_SECRET_KEY"
mc admin policy attach local rais-rw --user "$APP_ACCESS_KEY" 2>/dev/null || true

echo "[init] MinIO pronto."
