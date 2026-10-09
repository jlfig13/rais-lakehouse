"""Checks da Aula 09: arquivo real na landing e dicionário documentado."""
from pathlib import Path

import py7zr

from config.settings import LANDING

OBRIGATORIAS = ["municipio", "vinculo_ativo_31_12", "vl_remun_dezembro_nom", "vl_remun_dezembro_sm"]


def arquivos(ano):
    return sorted((LANDING / str(ano)).glob("*.7z"))


def test_a09_7z_na_landing(ano):
    assert arquivos(ano), f"Nenhum .7z em {LANDING / str(ano)}. Faça o passo 1."


def test_a09_7z_contem_txt(ano):
    for arq in arquivos(ano):
        with py7zr.SevenZipFile(arq, "r") as z:
            nomes = z.getnames()
        assert any(n.lower().endswith(".txt") for n in nomes), f"{arq.name} não contém .txt: {nomes[:5]}"


def test_a09_dicionario_preenchido():
    caminho = Path("docs/dicionario.md")
    assert caminho.exists(), "docs/dicionario.md não existe (passo 2)."
    texto = caminho.read_text(encoding="utf-8")
    faltando = [c for c in OBRIGATORIAS if c not in texto]
    assert not faltando, f"Colunas não documentadas: {faltando}"
