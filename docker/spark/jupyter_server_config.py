# [Complemento da plataforma] Configuração do JupyterLab para o site do curso.
import json
from pathlib import Path

c = get_config()  # noqa: F821 (objeto injetado pelo Jupyter ao carregar o arquivo)

# 1) Permite abrir o JupyterLab dentro do site (tela dividida das aulas e página Ambiente).
#    Só o site local (porta 8000) pode embutir; qualquer outra origem continua bloqueada.
c.ServerApp.tornado_settings = {
    "headers": {
        "Content-Security-Policy": (
            "frame-ancestors 'self' http://localhost:8000 http://127.0.0.1:8000"
        ),
    },
}


# 2) Um caderno de estudo por aula em estudos/aula-NN/, criado só se ainda não existir
#    (nunca sobrescreve o que você escreveu). É ele que abre ao lado do conteúdo.
def _celula(tipo: str, texto: str) -> dict:
    celula = {"cell_type": tipo, "metadata": {}, "source": texto}
    if tipo == "code":
        celula.update(outputs=[], execution_count=None)
    return celula


def _criar_cadernos(raiz: Path) -> None:
    try:
        import yaml

        aulas = yaml.safe_load((raiz / "curso" / "aulas.yml").read_text(encoding="utf-8"))["aulas"]
    except Exception as erro:  # sem metadados, o Jupyter sobe normalmente
        print(f"[estudos] cadernos não criados: {erro}")
        return
    for a in aulas:
        n = a["aula"]
        destino = raiz / "estudos" / f"aula-{n:02d}" / f"aula-{n:02d}.ipynb"
        if destino.exists():
            continue
        celulas = [_celula("markdown", f"# Aula {n:02d} — {a['titulo']}\n\n"
                           "Caderno de estudo: copie os blocos de código da aula (botão de copiar "
                           "no canto de cada bloco) e rode aqui. Crie outros arquivos nesta pasta "
                           "à vontade.")]
        if a["onde"] == "container":
            celulas += [
                _celula("code", 'from pyspark.sql import functions as F\n\n'
                                'from src.utils import get_spark\n\n'
                                f'spark = get_spark("aula-{n:02d}")\nspark'),
                _celula("markdown", "Spark SQL direto na célula, como no Databricks:"),
                _celula("code", "%%sql\nSELECT 1 AS teste"),
            ]
        else:
            celulas.append(_celula("markdown", "Os checks desta aula rodam no **host** "
                                   f"(`make check-host AULA={n:02d}`). Use este caderno para "
                                   "anotações e para rodar comandos com `!`."))
        nb = {"cells": celulas, "metadata": {"kernelspec": {"display_name": "Python 3",
              "language": "python", "name": "python3"}}, "nbformat": 4, "nbformat_minor": 5}
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")


_criar_cadernos(Path("/app"))
