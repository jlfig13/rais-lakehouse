"""Catálogo de dados do RAIS Lakehouse (Aula 17).

catalogo/rais.yml é a fonte das descrições. Este módulo:
1. valida o arquivo com Pydantic (campos obrigatórios, nomes, descrições não vazias);
2. confere com o schema real das tabelas Delta (coluna descrita que não existe, coluna sem
   descrição em tabela que exige catálogo completo);
3. grava as descrições como COMMENT nas tabelas e colunas Delta (o metadado viaja com a tabela);
4. exporta catalogo/rais.json, com tipos reais e regras de negócio, para servir de contexto a
   uma IA (text-to-SQL, busca semântica, geração de relatórios).

Uso:
    python -m src.catalogo            # valida e confere (não altera nada)
    python -m src.catalogo --aplicar  # também grava os COMMENTs e o JSON
"""
import argparse
import json
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from config.settings import LAKE

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = RAIZ / "catalogo" / "rais.yml"
SAIDA_JSON = RAIZ / "catalogo" / "rais.json"


class Coluna(BaseModel):
    nome: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    descricao: str = Field(min_length=5)
    unidade: str | None = None


class Tabela(BaseModel):
    nome: str = Field(pattern=r"^(bronze|silver|gold)\.[a-z][a-z0-9_]*$")
    caminho: str
    descricao: str = Field(min_length=10)
    grao: str
    atualizacao: str
    pergunta: str | None = None
    completa: bool = True  # exige descrição para todas as colunas da tabela
    colunas: list[Coluna]


class Catalogo(BaseModel):
    nome: str
    descricao: str
    dono: str
    regras: list[str] = []
    tabelas: list[Tabela]


def carregar(caminho: Path = CATALOGO) -> Catalogo:
    """Lê e valida o YAML; erros de formato aparecem com o caminho exato do campo."""
    return Catalogo.model_validate(yaml.safe_load(caminho.read_text(encoding="utf-8")))


def conferir(cat: Catalogo, schemas: dict[str, list[str]]) -> list[str]:
    """Compara o catálogo com {nome_tabela: [colunas reais]}. Devolve a lista de problemas."""
    problemas = []
    for t in cat.tabelas:
        reais = schemas.get(t.nome)
        if reais is None:
            problemas.append(f"{t.nome}: tabela não encontrada em {t.caminho}")
            continue
        descritas = {c.nome for c in t.colunas}
        for c in sorted(descritas - set(reais)):
            problemas.append(f"{t.nome}: coluna descrita não existe: {c}")
        if t.completa:
            for c in sorted(set(reais) - descritas):
                problemas.append(f"{t.nome}: coluna sem descrição: {c}")
    return problemas


def _texto(valor: str) -> str:
    return valor.replace("\\", "\\\\").replace("'", "\\'")


def aplicar(cat: Catalogo, spark) -> None:
    """Grava descrições como COMMENT/TBLPROPERTIES nas tabelas Delta.

    A gold é recriada com overwriteSchema a cada execução e perde os comentários:
    rode esta etapa sempre depois da gold (o pipeline tem a etapa "catalogo").
    """
    for t in cat.tabelas:
        alvo = f"delta.`{LAKE}/{t.caminho}`"
        props = {"comment": t.descricao, "rais.grao": t.grao, "rais.dono": cat.dono,
                 "rais.atualizacao": t.atualizacao}
        lista = ", ".join(f"'{k}' = '{_texto(v)}'" for k, v in props.items())
        spark.sql(f"ALTER TABLE {alvo} SET TBLPROPERTIES ({lista})")
        for c in t.colunas:
            texto = c.descricao + (f" Unidade: {c.unidade}." if c.unidade else "")
            spark.sql(f"ALTER TABLE {alvo} ALTER COLUMN `{c.nome}` COMMENT '{_texto(texto)}'")


def contexto_ia(cat: Catalogo, tipos: dict[str, dict[str, str]]) -> dict:
    """Catálogo em JSON para IA: tabelas, grão, colunas com tipo real, unidade e regras."""
    return {
        "catalogo": cat.nome,
        "descricao": cat.descricao,
        "regras_de_negocio": cat.regras,
        "tabelas": [
            {
                "nome": t.nome, "caminho": f"{LAKE}/{t.caminho}", "descricao": t.descricao,
                "pergunta": t.pergunta, "grao": t.grao, "atualizacao": t.atualizacao,
                "colunas": [
                    {"nome": c.nome, "tipo": tipos.get(t.nome, {}).get(c.nome),
                     "descricao": c.descricao, "unidade": c.unidade}
                    for c in t.colunas
                ],
            }
            for t in cat.tabelas
        ],
    }


def executar(spark, aplicar_no_lake: bool = False) -> None:
    """Valida e confere o catálogo; com aplicar_no_lake, grava COMMENTs e o JSON."""
    from src.delta_io import ler

    cat = carregar()
    tipos: dict[str, dict[str, str]] = {}
    for t in cat.tabelas:
        try:
            tipos[t.nome] = dict(ler(spark, f"{LAKE}/{t.caminho}").dtypes)
        except Exception:  # tabela ainda não criada: vira problema na conferência
            pass

    problemas = conferir(cat, {nome: list(cols) for nome, cols in tipos.items()})
    for prob in problemas:
        print(f"[catalogo] {prob}")
    if problemas:
        raise SystemExit(f"[catalogo] {len(problemas)} problema(s); corrija catalogo/rais.yml")
    print(f"[catalogo] ok: {len(cat.tabelas)} tabelas conferidas com o lake")

    if aplicar_no_lake:
        aplicar(cat, spark)
        SAIDA_JSON.write_text(json.dumps(contexto_ia(cat, tipos), ensure_ascii=False, indent=2),
                              encoding="utf-8")
        print(f"[catalogo] COMMENTs gravados; contexto para IA em {SAIDA_JSON.relative_to(RAIZ)}")


def main() -> None:
    from src.utils import get_spark

    p = argparse.ArgumentParser()
    p.add_argument("--aplicar", action="store_true", help="grava COMMENTs e catalogo/rais.json")
    executar(get_spark("rais-catalogo"), p.parse_args().aplicar)


if __name__ == "__main__":
    main()
