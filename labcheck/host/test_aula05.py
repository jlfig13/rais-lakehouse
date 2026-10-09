"""Checks da Aula 05: repositório organizado e sem segredos versionados."""
import os
import subprocess
import sys
from pathlib import Path

PASTAS = ["config", "docker/spark", "docker/minio", "docs", "notebooks", "scripts", "src", "staging", "tests"]


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True)


def test_a05_repositorio_git():
    assert git("rev-parse", "--is-inside-work-tree").returncode == 0, "Rode git init -b main (passo 1)."


def test_a05_env_ignorado():
    assert git("check-ignore", "-q", ".env").returncode == 0, ".env não está no .gitignore (passo 2)."


def test_a05_env_nao_versionado():
    r = git("ls-files", "--error-unmatch", ".env")
    assert r.returncode != 0, ".env está versionado! git rm --cached .env e TROQUE as senhas."


def test_a05_estrutura():
    faltando = [p for p in PASTAS if not Path(p).is_dir()]
    assert not faltando, f"Pastas ausentes: {faltando}"


def test_a05_settings_padrao():
    env = {k: v for k, v in os.environ.items() if not k.startswith("RAIS_")}
    r = subprocess.run([sys.executable, "-c", "from config.settings import LAKE; print(LAKE)"],
                       capture_output=True, text=True, env=env)
    assert r.stdout.strip() == "s3a://rais", f"Padrão inesperado: {r.stdout or r.stderr}"
