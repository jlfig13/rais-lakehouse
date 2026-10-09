"""Checks da Aula 03. Rodam no host, na raiz do projeto, com o ambiente no ar."""
import json
import subprocess


def compose(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "compose", *args], capture_output=True, text=True, timeout=120)


def servicos() -> dict:
    """Estado de cada serviço, incluindo os que já terminaram (-a)."""
    r = compose("ps", "-a", "--format", "json")
    assert r.returncode == 0, f"docker compose ps falhou: {r.stderr.strip()}"
    texto = r.stdout.strip()
    # Versões recentes imprimem um JSON por linha; algumas antigas, uma lista. Aceita os dois.
    if texto.startswith("["):
        itens = json.loads(texto)
    else:
        itens = [json.loads(linha) for linha in texto.splitlines() if linha.strip()]
    return {item["Service"]: item for item in itens}


def test_a03_compose_valido():
    r = compose("config", "-q")
    assert r.returncode == 0, f"Compose inválido ou variável faltando: {r.stderr.strip()}"


def test_a03_servicos_no_ar():
    s = servicos()
    for nome in ("minio", "spark"):
        estado = s.get(nome, {}).get("State")
        assert estado == "running", f"{nome} está '{estado}'. Veja: docker compose logs {nome}"


def test_a03_minio_init_ok():
    init = servicos().get("minio-init")
    assert init is not None, "minio-init nunca rodou. Rode: make up"
    assert init["State"] == "exited" and init["ExitCode"] == 0, (
        f"minio-init: estado {init['State']}, código {init['ExitCode']}. "
        "Veja: docker compose logs minio-init (Aula 04)"
    )


def test_a03_portas_so_locais():
    r = compose("config", "--format", "json")  # saída fica só na memória do teste
    assert r.returncode == 0, r.stderr.strip()
    expostas = [
        f"{nome}:{porta.get('published')}"
        for nome, svc in json.loads(r.stdout)["services"].items()
        for porta in svc.get("ports", [])
        if porta.get("host_ip") != "127.0.0.1"
    ]
    assert not expostas, f"Portas expostas fora de 127.0.0.1: {expostas}"
