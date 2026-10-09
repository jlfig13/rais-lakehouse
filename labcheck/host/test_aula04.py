"""Checks da Aula 04: o usuário da aplicação acessa só o bucket rais."""
import subprocess

PREFIXO = 'mc alias set app http://minio:9000 "$APP_ACCESS_KEY" "$APP_SECRET_KEY" >/dev/null && '


def como_app(comando: str) -> subprocess.CompletedProcess:
    """Roda um comando mc num container temporário, autenticado como rais-app."""
    return subprocess.run(
        ["docker", "compose", "run", "--rm", "--entrypoint", "/bin/sh",
         "minio-init", "-c", PREFIXO + comando],
        capture_output=True, text=True, timeout=180,
    )


def test_a04_bucket_existe():
    r = como_app("mc ls app/rais")
    assert r.returncode == 0, f"rais-app não lista o bucket: {r.stderr.strip()[-300:]}"


def test_a04_app_grava_no_rais():
    r = como_app("echo ok | mc pipe app/rais/_lab/aula04.txt && mc cat app/rais/_lab/aula04.txt "
                 "&& mc rm app/rais/_lab/aula04.txt")
    assert r.returncode == 0 and "ok" in r.stdout, f"Gravação falhou: {r.stderr.strip()[-300:]}"


def test_a04_app_nao_cria_bucket():
    r = como_app("mc mb app/proibido-aula04")
    assert r.returncode != 0, (
        "rais-app conseguiu criar um bucket: a política está ampla demais. "
        "Apague o bucket proibido-aula04 como root e revise policy-rais.json."
    )


def test_a04_app_nao_e_admin():
    r = como_app("mc admin user list app")
    assert r.returncode != 0, "rais-app executa comandos de administração. Revise a política."
