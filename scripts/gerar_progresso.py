"""Gera curso/docs/progresso.md a partir de progress/historico.jsonl."""
import json
from collections import defaultdict
from pathlib import Path

HISTORICO = Path("progress/historico.jsonl")
SAIDA = Path("curso/docs/progresso.md")


def main() -> None:
    ultimo = {}
    if HISTORICO.exists():
        for linha in HISTORICO.read_text(encoding="utf-8").splitlines():
            r = json.loads(linha)
            ultimo[(r["aula"], r["check"])] = r  # a execução mais recente vence

    por_aula = defaultdict(list)
    for (aula, _), r in ultimo.items():
        por_aula[aula].append(r)

    linhas = ["# Progresso", "", "Gerado por `make progresso` a partir de execuções reais.", "",
              "| Aula | Checks passando | Última execução |", "| --- | --- | --- |"]
    for aula in range(1, 18):
        rs = por_aula.get(aula, [])
        ok = sum(r["status"] == "passou" for r in rs)
        quando = max((r["ts"] for r in rs), default="—")
        linhas.append(f"| {aula:02d} | {ok}/{len(rs)} | {quando} |")

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"[progresso] {SAIDA}")


if __name__ == "__main__":
    main()
