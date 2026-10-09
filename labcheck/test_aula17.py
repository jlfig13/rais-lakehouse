"""Checks da Aula 17: catálogo válido, conferido com o lake e aplicado nas tabelas."""
import json
from pathlib import Path

from config.settings import GOLD
from src import catalogo
from src.delta_io import ler


def test_a17_catalogo_valido():
    """catalogo/rais.yml passa na validação do Pydantic."""
    cat = catalogo.carregar()
    assert any(t.nome.startswith("gold.") for t in cat.tabelas), "Nenhuma tabela gold no catálogo."


def test_a17_catalogo_confere_com_lake(spark):
    """Toda tabela existe e toda coluna de silver/gold está descrita."""
    cat = catalogo.carregar()
    schemas = {}
    for t in cat.tabelas:
        try:
            schemas[t.nome] = ler(spark, f"{catalogo.LAKE}/{t.caminho}").columns
        except Exception:
            pass
    problemas = catalogo.conferir(cat, schemas)
    assert not problemas, "Corrija catalogo/rais.yml:\n" + "\n".join(problemas)


def test_a17_comentarios_aplicados(spark):
    """As descrições estão gravadas na gold (rode: python -m src.catalogo --aplicar)."""
    linhas = spark.sql(f"DESCRIBE TABLE delta.`{GOLD}/gold_emprego_uf_ano`").collect()
    comentario = {r.col_name: r.comment for r in linhas}.get("qtd_vinculos")
    assert comentario, "qtd_vinculos sem COMMENT. Rode a etapa catalogo depois da gold."


def test_a17_contexto_ia():
    """catalogo/rais.json existe, com regras de negócio e tipos das colunas."""
    caminho = Path("catalogo/rais.json")
    assert caminho.exists(), "Rode: python -m src.catalogo --aplicar"
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    assert dados["regras_de_negocio"], "Sem regras de negócio no contexto para IA."
    assert all(c["tipo"] for t in dados["tabelas"] if t["nome"].startswith("gold.")
               for c in t["colunas"]), "Colunas da gold sem tipo no JSON."
