"""Checks da Aula 16: qualidade e publicação."""
import subprocess
from pathlib import Path

SECOES_README = ["## Arquitetura", "## Como rodar", "## Decisões técnicas", "## Limitações"]


def rodar(*cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), capture_output=True, text=True)


def test_a16_testes_passam():
    r = rodar("pytest", "-q", "tests")
    assert r.returncode == 0, r.stdout[-800:]


def test_a16_lint_passa():
    r = rodar("ruff", "check", ".")
    assert r.returncode == 0, r.stdout[-800:]


def test_a16_workflow_ci():
    ci = Path(".github/workflows/ci.yml")
    assert ci.exists(), "Crie .github/workflows/ci.yml (passo 3)."
    texto = ci.read_text()
    assert "pytest" in texto and "ruff" in texto and "setup-java" in texto


def test_a16_readme_completo():
    texto = Path("README.md").read_text(encoding="utf-8")
    faltando = [s for s in SECOES_README if s not in texto]
    assert not faltando, f"Seções ausentes no README: {faltando}"


def test_a16_licenca():
    assert Path("LICENSE").exists(), "Acrescente um arquivo LICENSE (passo 7)."
