"""Checks da Aula 15: configuração que cabe no container e decisão registrada."""
from pathlib import Path

import pytest

UNIDADES = {"k": 1024, "m": 1024**2, "g": 1024**3, "t": 1024**4}


def em_bytes(valor: str) -> int:
    valor = valor.strip().lower()
    if valor[-1] in UNIDADES:
        return int(float(valor[:-1]) * UNIDADES[valor[-1]])
    return int(valor)


def limite_container() -> int | None:
    for arquivo in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        p = Path(arquivo)
        if p.exists():
            texto = p.read_text().strip()
            return None if texto == "max" else int(texto)
    return None


def test_a15_memoria_cabe_no_container(spark):
    limite = limite_container()
    if limite is None:
        pytest.skip("Container sem limite de memória visível.")
    driver = em_bytes(spark.conf.get("spark.driver.memory"))
    assert driver <= 0.8 * limite, (
        f"SPARK_MEM ({driver / 1024**3:.1f} GB) acima de 80% do container ({limite / 1024**3:.1f} GB)."
    )


def test_a15_threads_explicitas(spark):
    assert spark.conf.get("spark.master") != "local[*]", "Use SPARK_THREADS explícito."


def test_a15_benchmark_registrado():
    p = Path("docs/benchmark.csv")
    assert p.exists(), "Rode o passo 4."
    linhas = [linha for linha in p.read_text().splitlines() if linha.strip()]
    assert linhas[0] == "threads,shuffle,segundos" and len(linhas) >= 4, f"CSV incompleto: {linhas[:3]}"


def test_a15_adr_tuning():
    texto = Path("docs/decisoes.md").read_text(encoding="utf-8")
    assert "SPARK_THREADS" in texto and "SPARK_SHUFFLE" in texto, "Registre a configuração escolhida como ADR."
