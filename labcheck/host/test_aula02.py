"""Checks da Aula 02. Rodam no host (WSL/Linux), pois usam o CLI do Docker."""
import os
import subprocess

IMAGEM = "rais-spark:local"

JARS_ESPERADOS = {
    "hadoop-aws-3.3.4.jar",
    "aws-java-sdk-bundle-1.12.262.jar",
    "delta-spark_2.12-3.2.0.jar",
    "delta-storage-3.2.0.jar",
}

LISTAR_JARS = (
    "import glob, os, pyspark; "
    "d = os.path.join(os.path.dirname(pyspark.__file__), 'jars'); "
    "print('\\n'.join(os.path.basename(p) for p in glob.glob(d + '/*.jar')))"
)


def rodar(*args: str) -> subprocess.CompletedProcess:
    """Executa um comando do Docker sem lançar exceção; o teste decide o que é falha."""
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=300)


def na_imagem(*cmd: str) -> subprocess.CompletedProcess:
    return rodar("run", "--rm", IMAGEM, *cmd)


def test_a02_imagem_existe():
    r = rodar("image", "inspect", IMAGEM)
    assert r.returncode == 0, f"Imagem {IMAGEM} não existe. Faça o passo 6 da Aula 02."


def test_a02_java_17():
    r = na_imagem("java", "-version")
    saida = r.stdout + r.stderr  # java -version escreve na saída de erro
    assert r.returncode == 0 and '"17' in saida, (
        f"Java 17 não encontrado: {saida.strip()[:200]}. Confira o bloco 3 e o FROM -bookworm."
    )


def test_a02_pyspark_delta():
    r = na_imagem("python", "-c", "import pyspark, delta; print(pyspark.__version__)")
    assert r.returncode == 0, f"Import falhou: {r.stderr.strip()[-300:]}"
    assert r.stdout.strip() == "3.5.3", f"PySpark {r.stdout.strip()} != 3.5.3. Confira requirements.txt."


def test_a02_jars_s3a_delta():
    r = na_imagem("python", "-c", LISTAR_JARS)
    faltando = JARS_ESPERADOS - set(r.stdout.split())
    assert not faltando, f"JARs ausentes: {sorted(faltando)}. Rebuild com --no-cache e confira o bloco 5."


def test_a02_usuario_nao_root():
    r = na_imagem("id", "-u")
    uid = r.stdout.strip()
    assert uid != "0", "O container roda como root. Confira USER app no bloco 7."
    assert uid == str(os.getuid()), (
        f"UID do container ({uid}) != seu UID ({os.getuid()}). "
        'Rebuild com --build-arg HOST_UID="$(id -u)".'
    )
