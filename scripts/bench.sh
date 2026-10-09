#!/usr/bin/env bash
# Mede o tempo da silver variando threads e partições de shuffle.
# Origem: Guia Parte 14.6 / Aula 15. Rode DENTRO do container (make shell).
set -euo pipefail
ANO="${1:-2022}"

printf "threads,shuffle,segundos\n"
for t in 2 4 6; do
  for p in 16 32 64; do
    inicio=$(date +%s)
    SPARK_THREADS=$t SPARK_SHUFFLE=$p \
      python -m src.run_pipeline --anos "$ANO" --etapas silver > /dev/null 2>&1
    printf "%s,%s,%s\n" "$t" "$p" "$(( $(date +%s) - inicio ))"
  done
done
