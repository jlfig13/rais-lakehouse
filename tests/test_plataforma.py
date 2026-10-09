"""Testes da plataforma do curso: API de progresso e geração das páginas (sem Spark)."""
import json

from scripts.gerar_curso import limpar_conteudo
from scripts.portal_api import aplicar, resumo, ultimos_resultados


def test_ultimo_resultado_vence():
    linhas = [
        json.dumps({"ts": "2026-10-01T10:00:00", "aula": 7, "check": "a07_x", "status": "falhou"}),
        json.dumps({"ts": "2026-10-02T10:00:00", "aula": 7, "check": "a07_x", "status": "passou"}),
        "",
    ]
    assert ultimos_resultados(linhas)[7]["a07_x"]["status"] == "passou"


def test_resumo_conta_so_checks_declarados():
    resultados = {7: {"a07_x": {"ts": "t1", "status": "passou"},
                      "a07_antigo": {"ts": "t2", "status": "falhou"}}}
    r = resumo({7: ["a07_x", "a07_y"], 8: []}, resultados, {})
    assert r["7"]["checks"] == {"declarados": 2, "passou": 1, "falhou": 0, "ultima": "t2",
                                "itens": {"a07_x": "passou"}}
    assert r["8"]["checks"]["ultima"] is None and r["8"]["concluida_em"] is None


def test_aplicar_marca_desmarca_e_conclui():
    estudo = {}
    aplicar(estudo, {"aula": 7, "criterio": " Sei explicar X ", "marcado": True})
    assert estudo["7"]["criterios"] == {"Sei explicar X": True}
    aplicar(estudo, {"aula": "7", "criterio": "Sei explicar X", "marcado": False})
    assert estudo["7"]["criterios"] == {}
    assert aplicar(estudo, {"aula": 7, "concluida": True})["concluida_em"]
    assert aplicar(estudo, {"aula": 7, "concluida": False})["concluida_em"] is None


def test_limpar_conteudo():
    md = "\n".join([
        "# Aula 07 — Título",
        "",
        "Oct 9, 2026 · @Fulano",
        "",
        "Introdução.",
        "",
        "```yaml",
        "aula: 7",
        "```",
        "",
        "&#91;embedded content: Diagrama X\\]",
        "",
        "**Checklist manual:** \\[ \\] item a · \\[ \\] item b",
    ])
    saida = limpar_conteudo(md, "https://doc")
    assert saida.startswith("Introdução.")
    assert "aula: 7" not in saida
    assert '!!! note "Diagrama interativo"' in saida and "(https://doc)" in saida
    assert "- [ ] item a\n- [ ] item b" in saida
