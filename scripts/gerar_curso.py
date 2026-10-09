"""Gera as páginas do site do curso (curso/docs/) a partir de curso/aulas.yml e de labcheck/.

[Complemento da plataforma] Fonte única: os metadados ficam no YAML e a lista de checks é
lida dos próprios arquivos de teste (com `ast`, sem importar nada). Assim o site nunca
descreve um check que não existe. O texto de cada aula vem de curso/conteudo/aula-NN.md
(export em Markdown do documento da aula); sem ele, a página avisa que falta o texto.

Uso: python -m scripts.gerar_curso
"""
import ast
import re
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parent.parent
META = RAIZ / "curso" / "aulas.yml"
DOCS = RAIZ / "curso" / "docs"
CONTEUDO = RAIZ / "curso" / "conteudo"
GUIA = RAIZ / "docs" / "guia" / "rais-lakehouse-guia.md"
ONDE = {"host": "Host (WSL/Linux)", "container": "Container spark"}
COMPLEMENTO = '<span class="rl-complemento">Complemento didático</span>'


# ---------------------------------------------------------------------- guia original
def fora_de_codigo(texto: str, funcao) -> str:
    """Aplica `funcao` só ao texto corrido: blocos ``` e `código inline` ficam intactos."""
    partes = re.split(r"(^```.*?^```[^\n]*$)", texto, flags=re.M | re.S)
    for i in range(0, len(partes), 2):
        trechos = re.split(r"(`[^`\n]+`)", partes[i])
        trechos[::2] = [funcao(t) for t in trechos[::2]]
        partes[i] = "".join(trechos)
    return "".join(partes)


def url_guia(base: str, parte: str) -> str:
    """'4.5' -> base + 'parte-04.md#parte-4-5'; 'B' -> base + 'apendice-b.md'."""
    if parte.isalpha():
        return f"{base}apendice-{parte.lower()}.md"
    numero, _, secao = parte.partition(".")
    ancora = f"#parte-{numero}-{secao}" if secao else ""
    return f"{base}parte-{int(numero):02d}.md{ancora}"


def linkar_guia(texto: str, base: str, todo_apendice: bool = False) -> str:
    """Transforma citações ('guia, Parte 4.5', 'Partes 5.1–5.2', 'Apêndice B do guia') em links.

    Nas aulas, "Apêndice X" sem menção ao guia é dos apêndices do curso (A–G) e não vira link.
    """
    def partes(m: re.Match) -> str:
        nums = re.sub(r"\d+(?:\.\d+)?", lambda n: f"[{n.group(0)}]({url_guia(base, n.group(0))})",
                      m.group(2))
        return f"{m.group(1)} {nums}"

    def apendice(m: re.Match) -> str:
        return f"[Apêndice {m.group(1)}]({url_guia(base, m.group(1))})"

    def aplicar(t: str) -> str:
        t = re.sub(r"\b(Partes?) (\d+(?:\.\d+)?(?:(?:\s*[,–-]\s*|\s+e\s+|\s+a\s+)\d+(?:\.\d+)?)*)",
                   partes, t)
        if todo_apendice:
            return re.sub(r"\bApêndice ([A-D])\b", apendice, t)
        t = re.sub(r"(?:(?<=guia, )|(?<=Guia ))Apêndice ([A-D])\b", apendice, t)
        return re.sub(r"\bApêndice ([A-D])(?= do guia)", apendice, t)

    return fora_de_codigo(texto, aplicar)


def marcar_complemento(texto: str) -> str:
    """'**\\[Complemento didático\\]**' vira uma etiqueta visível (ver assets/portal.css)."""
    def trocar(m: re.Match) -> str:  # "**\[Complemento didático\] — título**" mantém o título
        return COMPLEMENTO + (f" **{m.group(1)}**" if m.group(1) else "")

    return fora_de_codigo(texto, lambda t: re.sub(
        r"\*\*\\\[Complemento(?: didático)?\\\](?:\s*—\s*)?([^*]*)\*\*", trocar, t))


def paginas_guia() -> dict[str, str]:
    """Divide o guia em uma página por Parte/Apêndice, com âncoras estáveis (#parte-4-5)."""
    if not GUIA.exists():
        return {}
    paginas: dict[str, list[str]] = {"index": []}
    titulos: list[tuple[str, str]] = []
    atual, em_codigo = "index", False
    for linha in GUIA.read_text(encoding="utf-8").splitlines():
        if linha.startswith("```"):
            em_codigo = not em_codigo
        m = None if em_codigo else re.match(r"^# (?:Parte (\d+)|Apêndice ([A-D])) — ", linha)
        if m:
            atual = (f"parte-{int(m.group(1)):02d}" if m.group(1)
                     else f"apendice-{m.group(2).lower()}")
            titulos.append((atual, linha[2:]))
            paginas[atual] = []
        elif not em_codigo:
            secao = re.match(r"^## (\d+)\.(\d+) ", linha)
            if secao:
                linha += f" {{ #parte-{secao.group(1)}-{secao.group(2)} }}"
        paginas[atual].append(linha)

    # Capa: introdução do guia + sumário com links (no lugar do sumário em texto)
    capa = "\n".join(paginas["index"])
    capa = re.sub(r"## Sumário\n.*?\n---\n", "", capa, flags=re.S)
    capa = capa.replace("# RAIS Lakehouse —", "# Guia original — RAIS Lakehouse —", 1)
    capa += "\n## Sumário\n\n" + "\n".join(f"- [{t}]({nome}.md)" for nome, t in titulos) + "\n"
    saida = {"index": capa}
    for nome, linhas in paginas.items():
        if nome != "index":
            saida[nome] = "\n".join(linhas).strip() + "\n"
    return {nome: "<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->\n\n"
            + linkar_guia(md, "", todo_apendice=True) for nome, md in saida.items()}


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


def limpar_conteudo(md: str) -> str:
    """Adapta o export do documento à página: tira o repetido e o que não renderiza."""
    linhas = md.splitlines()
    # Título (a página gera o seu) e a linha de data/autor do documento
    while linhas and (not linhas[0].strip() or linhas[0].startswith("# ")
                      or re.match(r"^[A-Z][a-z]{2} \d{1,2}, \d{4}", linhas[0])):
        linhas.pop(0)
    texto = "\n".join(linhas)
    # Bloco de metadados (já está na tabela do topo da página)
    texto = re.sub(r"```yaml\n(?:#[^\n]*\n)?aula: .*?```\n+", "", texto, count=1, flags=re.S)
    # Diagramas interativos do documento não vêm no export: sai o marcador vazio
    texto = re.sub(r"&#91;embedded content: .+?\\\]\n*", "", texto)
    # Links para documentos privados do claude.ai não abrem para quem lê o site: fica só o texto
    texto = re.sub(r"\[([^\]]+)\]\(https://claude\.ai/[^)]+\)", r"\1", texto)
    # Checklists escritos numa linha só ("**Checklist manual:** \[ \] a · \[ \] b") viram listas
    def lista(m: re.Match) -> str:
        itens = [i.strip() for i in re.split(r"\s*·\s*", m.group(2))]
        itens = [re.sub(r"^\\\[ \\\]\s*", "", i) for i in itens if i]
        return f"{m.group(1)}\n\n" + "\n".join(f"- [ ] {i}" for i in itens)

    texto = re.sub(r"^(\*\*[^*\n]+:?\*\*:?)\s*(\\\[ \\\].*)$", lista, texto, flags=re.M)
    return texto.strip() + "\n"


def qtd_criterios(n: int) -> int:
    """Itens de checklist da aula: são os critérios que a página deixa marcar."""
    fonte = CONTEUDO / f"aula-{n:02d}.md"
    if not fonte.exists():
        return 0
    return len(re.findall(r"^\s*- \[ \] ", limpar_conteudo(fonte.read_text(encoding="utf-8")),
                          flags=re.M))


def arquivo_lab(a: dict) -> str:
    """Primeiro arquivo de entrega que existe e abre bem no JupyterLab (para o botão da página)."""
    for e in a["entrega"]:
        caminho = e.split(" ")[0]
        if (caminho.endswith((".py", ".ipynb")) and not Path(caminho).name.startswith("__")
                and (RAIZ / caminho).exists()):
            return caminho
    return ""


def pagina_aula(a: dict) -> str:
    n = a["aula"]
    arq = arquivo_de_checks(n)
    lista = checks(arq) if arq else []
    fonte = CONTEUDO / f"aula-{n:02d}.md"
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
        "<!-- Página GERADA por scripts/gerar_curso.py. Edite aulas.yml e curso/conteudo/. -->",
        "",
        f'<div class="rl-aula" data-aula="{n}" data-onde="{a["onde"]}" '
        f'data-lab="{arquivo_lab(a)}"></div>',
        "",
        "| | |",
        "| --- | --- |",
        f"| Origem no guia | {linkar_guia(', '.join(a['origem']), '../guia/')} |",
        f"| Depende de | {dep} |",
        f"| Entregas | {', '.join(f'`{e}`' for e in a['entrega'])} |",
        f"| Onde os checks rodam | {ONDE[a['onde']]} |",
        "",
    ]
    if fonte.exists():
        texto = limpar_conteudo(fonte.read_text(encoding="utf-8"))
        linhas += [marcar_complemento(linkar_guia(texto, "../guia/")), ""]
    else:
        linhas += [
            '!!! warning "Conteúdo ainda não importado"',
            f"    O texto desta aula ainda não está em `curso/conteudo/aula-{n:02d}.md`.",
            "",
        ]
    linhas += ["## Checks automáticos", ""]
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


def pagina_indice(meta: dict) -> str:
    linhas = [
        "# RAIS Lakehouse — Plataforma de aprendizagem",
        "",
        "Curso prático de PySpark, Delta Lake e MinIO construindo um lakehouse com os "
        "microdados da RAIS (bronze → silver → gold), tudo open source e local.",
        "",
        "## Como estudar",
        "",
        "1. Abra a aula na trilha abaixo e estude o conteúdo na própria página.",
        "2. Faça o tutorial e o laboratório no [Ambiente](ambiente.md) (JupyterLab e MinIO "
        "integrados), no terminal ou no VS Code.",
        "3. Marque os critérios de conclusão na página da aula: eles ficam gravados em "
        "`progress/estudo.json`.",
        "4. Rode os checks da aula. Só avance quando passarem; o resultado aparece na trilha.",
        "",
        "> Os checks verificam o **seu** ambiente. Este site não executa código e não "
        "mostra resultados que você não produziu.",
        "",
        "## Trilha",
        "",
        '<div id="rl-resumo"></div>',
        "",
        "| Aula | Título | Depende de | Checks | Progresso |",
        "| --- | --- | --- | --- | --- |",
    ]
    for a in meta["aulas"]:
        n = a["aula"]
        arq = arquivo_de_checks(n)
        dep = ", ".join(f"{d:02d}" for d in a["depende_de"]) or "—"
        linhas.append(f"| {n:02d} | [{a['titulo']}](aulas/aula-{n:02d}.md) | {dep} | "
                      f"{len(checks(arq)) if arq else 0} | "
                      f'<span class="rl-trilha" data-aula="{n}" '
                      f'data-criterios="{qtd_criterios(n)}">—</span> |')
    linhas += [
        "",
        "Apêndices A–G: [página de apêndices](apendices.md). "
        "Guia em que o curso se baseia: [Guia original](guia/index.md).",
    ]
    return "\n".join(linhas) + "\n"


def pagina_apendices(meta: dict) -> str:
    fonte = CONTEUDO / "apendices.md"
    if fonte.exists():
        texto = limpar_conteudo(fonte.read_text(encoding="utf-8"))
        return "# Apêndices\n\n" + marcar_complemento(linkar_guia(texto, "guia/"))
    linhas = ["# Apêndices", "", "O texto dos apêndices ainda não está em "
              "`curso/conteudo/apendices.md`.", ""]
    linhas += [f"- Apêndice {t}" for t in meta["apendices"]]
    return "\n".join(linhas) + "\n"


def pagina_ambiente() -> str:
    return "\n".join([
        "# Ambiente",
        "",
        "<!-- Página GERADA por scripts/gerar_curso.py. -->",
        "",
        "JupyterLab, console do MinIO e Spark UI num só lugar. As ferramentas abrem aqui "
        "dentro; se preferir, use **abrir em nova aba**.",
        "",
        '<div id="rl-ambiente"></div>',
        "",
        '??? info "Primeiro acesso"',
        "    - **JupyterLab:** na primeira vez, cole o token (`JUPYTER_TOKEN` do `.env`).",
        "    - **MinIO:** entre com `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` do `.env`.",
        "    - **Spark UI:** só existe enquanto há uma sessão Spark aberta (Aula 06).",
        "",
    ]) + "\n"


def main() -> None:
    meta = yaml.safe_load(META.read_text(encoding="utf-8"))
    (DOCS / "aulas").mkdir(parents=True, exist_ok=True)
    for a in meta["aulas"]:
        destino = DOCS / "aulas" / f"aula-{a['aula']:02d}.md"
        destino.write_text(pagina_aula(a), encoding="utf-8")
    (DOCS / "index.md").write_text(pagina_indice(meta), encoding="utf-8")
    (DOCS / "apendices.md").write_text(pagina_apendices(meta), encoding="utf-8")
    (DOCS / "ambiente.md").write_text(pagina_ambiente(), encoding="utf-8")
    (DOCS / "guia").mkdir(exist_ok=True)
    for nome, md in paginas_guia().items():
        (DOCS / "guia" / f"{nome}.md").write_text(md, encoding="utf-8")
    print(f"[curso] {len(meta['aulas'])} aulas geradas em {DOCS}")


if __name__ == "__main__":
    main()
