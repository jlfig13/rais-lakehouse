"""Configurações do projeto, lidas de variáveis de ambiente (com padrões seguros).

Origem: Guia Parte 7.2 / Aula 05.
"""
import os
from pathlib import Path

# --- Staging local (arquivos temporários) ---
STAGING = Path(os.getenv("RAIS_STAGING", "/staging"))
LANDING = STAGING / "landing"
RAW = STAGING / "raw"
EXPORT = STAGING / "export"

# --- Lake (Delta no MinIO). Para testar sem MinIO: RAIS_LAKE=file:///tmp/lake ---
LAKE = os.getenv("RAIS_LAKE", "s3a://rais")
BRONZE = f"{LAKE}/bronze/rais_vinculos"
SILVER = f"{LAKE}/silver/rais_vinculos"
GOLD = f"{LAKE}/gold"

# --- Anos (ajuste ao último ano-base com microdados publicados) ---
ANOS = list(range(2019, 2025))
