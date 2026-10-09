"""Check da Aula 01: decisões de arquitetura registradas."""
from pathlib import Path

DECISOES = Path("docs/decisoes.md")


def test_a01_adrs_registrados():
    assert DECISOES.exists(), "docs/decisoes.md não existe. Faça o tutorial da Aula 01."
    texto = DECISOES.read_text(encoding="utf-8")
    qtd = texto.count("## ADR-")
    assert qtd >= 6, f"{qtd} ADRs encontrados; a Aula 01 pede os 6 do guia."
    assert "## Contratos de camada" in texto, "Faltam os contratos de camada (passo 4)."
