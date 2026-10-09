# [Complemento da plataforma] Magic %%sql nos notebooks, como as células SQL do Databricks.
# Instalado na imagem em ~/.ipython/profile_default/startup/ (roda ao abrir cada kernel).
#
#   %%sql                      roda Spark SQL e mostra até 50 linhas
#   %%sql resultado 200        guarda o DataFrame em `resultado` e mostra até 200 linhas
from IPython import get_ipython
from IPython.core.magic import register_cell_magic


def _spark():
    ip = get_ipython()
    sessao = ip.user_ns.get("spark")
    if sessao is None:  # cria só se a célula precisar, com a mesma configuração do projeto
        from src.utils import get_spark

        sessao = ip.user_ns["spark"] = get_spark("notebook")
    return sessao


@register_cell_magic
def sql(linha, celula):
    """Executa a célula como Spark SQL. Argumentos opcionais: [variavel] [limite]."""
    args = linha.split()
    limite = int(args[-1]) if args and args[-1].isdigit() else 50
    nome = args[0] if args and not args[0].isdigit() else None
    df = _spark().sql(celula)
    if nome:
        get_ipython().user_ns[nome] = df
    return df.limit(limite).toPandas()


del sql
