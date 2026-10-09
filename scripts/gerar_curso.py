"""Gera as páginas do site do curso (curso/docs/) a partir de curso/aulas.yml e de labcheck/.

[Complemento da plataforma] Fonte única: os metadados ficam no YAML e a lista de checks é
lida dos próprios arquivos de teste (com `ast`, sem importar nada). Assim o site nunca
descreve um check que não existe.

Uso: python -m scripts.gerar_curso
"""
import ast
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
META = RAIZ / "curso" / "aulas.yml"
DOCS = RAIZ / "curso" / "docs"
ONDE = {"host": "Host (WSL/Linux)", "container": "Container spark"}


def arquivo_de_checks(aula: int) -> Path | None:
    for pasta in ("labcheck/host", "labcheck"):
        p = RAIZ / pasta / f"test_aula{aula:02d}.py"
        if p.exists():
            return p
    return None


def checks(arquivo: Path) -> list[tuple[str, str]]:
    """[(id, descrição)] a partir das funções test_* e de suas docstrings."""
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    saida = []
    for no in arvore.body:
        if isinstance(no, ast.FunctionDef) and no.name.startswith("test_"):
            doc = (ast.get_docstring(no) or "").splitlines()
            ident = no.name.removeprefix("test_")
            # Sem docstring: a07_media_por_sexo -> "media por sexo"
            legivel = ident.split("_", 1)[1].replace("_", " ")
            saida.append((ident, doc[0] if doc else legivel))
    return saida


def comando(aula: int, onde: str, arquivo: Path) -> str:
    if onde == "host":
        if arquivo.parent.name == "host":
            return f"make check-host AULA={aula:02d}"
        rel = arquivo.relative_to(RAIZ)
        return f".venv-host/bin/pytest -v {rel}   # ou: make check AULA={aula:02d}"
    return f"make check AULA={aula:02d} ANO=2022"


def pagina_aula(a: dict, base: str) -> str:
    n = a["aula"]
    arq = arquivo_de_checks(n)
    lista = checks(arq) if arq else []
    dep = ", ".join(f"[Aula {d:02d}](aula-{d:02d}.md)" for d in a["depende_de"]) or "—"
    linhas = [
        "---",
        f"aula: {n}",
        f'titulo: "{a["titulo"]}"',
        f"origem: {a['origem']}",
        f"depende_de: {a['depende_de']}",
        f"checks: {[c for c, _ in lista]}",
        "---",
        "",
        f"# Aula {n:02d} — {a['titulo']}",
        "",
        "<!-- Página GERADA por scripts/gerar_curso.py. Edite curso/aulas.yml. -->",
        "",
        f"**Conteúdo completo da aula (13 seções):** [abrir o documento da Aula {n:02d}]"
        f"({base}/{a['doc']})",
        "",
        "| | |",
        "| --- | --- |",
        f"| Origem no guia | {', '.join(a['origem'])} |",
        f"| Depende de | {dep} |",
        f"| Entregas | {', '.join(f'`{e}`' for e in a['entrega'])} |",
        f"| Onde os checks rodam | {ONDE[a['onde']]} |",
        "",
        "## Validação",
        "",
    ]
    if arq:
        linhas += [
            "```bash",
            comando(n, a["onde"], arq),
            "```",
            "",
            f"Arquivo: `{arq.relative_to(RAIZ)}`. Cada execução grava o resultado em "
            "`progress/historico.jsonl`; depois rode `make progresso` para atualizar a página "
            "[Progresso](../progresso.md).",
            "",
            "| Check | O que verifica |",
            "| --- | --- |",
        ]
        linhas += [f"| `{c}` | {d} |" for c, d in lista]
    else:
        linhas.append("Esta aula não tem checks automáticos.")
    return "\n".join(linhas) + "\n"


def pagina_indice(meta: dict, base: str) -> str:
    linhas = [
        "# RAIS Lakehouse — Plataforma de aprendizagem",
        "",
        "Curso prático de PySpark, Delta Lake e MinIO construindo um lakehouse com os "
        "microdados da RAIS (bronze → silver → gold), tudo open source e local.",
        "",
        "## Como estudar",
        "",
        "1. Abra a aula na trilha abaixo e leia o documento completo (link no topo da página).",
        "2. Faça o tutorial e o laboratório no seu ambiente (terminal, VS Code ou JupyterLab).",
        "3. Rode os checks da aula. Só avance quando passarem.",
        "4. Rode `make progresso` e veja a página [Progresso](progresso.md).",
        "",
        "> Os checks verificam o **seu** ambiente. Este site não executa código e não "
        "mostra resultados que você não produziu.",
        "",
        "## Trilha",
        "",
        "| Aula | Título | Depende de | Checks |",
        "| --- | --- | --- | --- |",
    ]
    for a in meta["aulas"]:
        n = a["aula"]
        arq = arquivo_de_checks(n)
        dep = ", ".join(f"{d:02d}" for d in a["depende_de"]) or "—"
        linhas.append(f"| {n:02d} | [{a['titulo']}](aulas/aula-{n:02d}.md) | {dep} | "
                      f"{len(checks(arq)) if arq else 0} |")
    linhas += [
        "",
        f"Apêndices A–G: [página de apêndices](apendices.md). "
        f"Diagnóstico e plano técnico da plataforma: [documento]({base}/{meta['plano_doc']}).",
    ]
    return "\n".join(linhas) + "\n"


def pagina_apendices(meta: dict, base: str) -> str:
    linhas = ["# Apêndices", "", f"Todos os apêndices estão num único documento: "
              f"[abrir os apêndices]({base}/{meta['apendices_doc']}).", ""]
    linhas += [f"- Apêndice {t}" for t in meta["apendices"]]
    return "\n".join(linhas) + "\n"


def main() -> None:
    meta = yaml.safe_load(META.read_text(encoding="utf-8"))
    base = meta["docs_base"]
    (DOCS / "aulas").mkdir(parents=True, exist_ok=True)
    for a in meta["aulas"]:
        destino = DOCS / "aulas" / f"aula-{a['aula']:02d}.md"
        destino.write_text(pagina_aula(a, base), encoding="utf-8")
    (DOCS / "index.md").write_text(pagina_indice(meta, base), encoding="utf-8")
    (DOCS / "apendices.md").write_text(pagina_apendices(meta, base), encoding="utf-8")
    print(f"[curso] {len(meta['aulas'])} aulas geradas em {DOCS}")


if __name__ == "__main__":
    main()
