"""Configuração comum dos checks: opção --ano, fixture spark e registro do progresso."""
import json
import os
import re
from datetime import datetime
from pathlib import Path

import pytest

HISTORICO = Path("progress/historico.jsonl")


def pytest_addoption(parser):
    parser.addoption("--ano", type=int, default=2022, help="ano-base usado pelos checks")


@pytest.fixture(scope="session")
def ano(request):
    return request.config.getoption("--ano")


@pytest.fixture(scope="session")
def spark():
    if os.getenv("LABCHECK_SEM_LAKE") == "1":
        # [Complemento da plataforma] Sessão local SEM Delta/MinIO. Serve só para os
        # checks que não tocam o lake (Aulas 07 e 08), por exemplo no CI.
        from pyspark.sql import SparkSession

        sessao = (SparkSession.builder.master("local[1]").appName("labcheck-sem-lake")
                  .config("spark.ui.enabled", "false").getOrCreate())
        yield sessao
        sessao.stop()
        return

    from src.utils import get_spark  # importa só se um check precisar (o host não tem PySpark)

    sessao = get_spark("labcheck")
    yield sessao
    sessao.stop()


def pytest_runtest_logreport(report):
    """Grava uma linha por check em progress/historico.jsonl."""
    if report.when != "call" and not (report.when == "setup" and report.skipped):
        return
    m = re.search(r"test_aula(\d+)\.py::test_(\w+)", report.nodeid)
    if not m:
        return
    status = "passou" if report.passed else "pulou" if report.skipped else "falhou"
    linha = {
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "aula": int(m.group(1)),
        "check": m.group(2),
        "status": status,
        "detalhe": str(report.longrepr)[-300:] if report.failed else "",
        "origem": "execucao_real",
    }
    HISTORICO.parent.mkdir(exist_ok=True)
    with HISTORICO.open("a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")
