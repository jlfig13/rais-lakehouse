"""Gera uma AMOSTRA SINTÉTICA no formato dos microdados de vínculos da RAIS.

[Complemento da plataforma] Estes dados são INVENTADOS. Servem só para testes de
unidade, testes de integração no CI e para praticar sem baixar a RAIS real.
Nunca use números calculados sobre eles como se fossem resultados da RAIS.

O formato imita o descrito no guia (Parte 6.1): separador ';', encoding latin-1,
decimal com vírgula, cabeçalho com acentos e espaços e alguns valores inválidos.
Os nomes de coluna são ILUSTRATIVOS: confira os nomes reais no dicionário oficial.

Uso:
    python -m labs.amostra.gerar_amostra --saida staging/raw/2022 --linhas 500
    python -m labs.amostra.gerar_amostra --saida staging/landing/2022 --7z
"""
import argparse
import random
from pathlib import Path

CABECALHO = [
    "Município", "CNAE 2.0 Classe", "CBO Ocupação 2002", "Vínculo Ativo 31/12",
    "Sexo Trabalhador", "Escolaridade após 2005", "Raça Cor", "Idade", "Tempo Emprego",
    "Mês Desligamento", "Motivo Desligamento", "Tamanho Estabelecimento", "Natureza Jurídica",
    "Vl Remun Dezembro Nom", "Vl Remun Média Nom", "Vl Remun Dezembro (SM)", "Vl Remun Média (SM)",
]

# Municípios ilustrativos (6 dígitos; 2 primeiros = UF)
MUNICIPIOS = ["261160", "260790", "355030", "292740", "230440", "330455"]
CNAES = ["47113", "86101", "84116", "10112", "62015", "41204"]
CBOS = ["411005", "322205", "517330", "784205", "212405"]
SALARIO_MINIMO = 1212.00  # valor ilustrativo usado só para gerar a coluna (SM)
NOME_ARQUIVO = "RAIS_VINC_PUB_SINTETICO.txt"


def _br(valor: float, casas: int = 2) -> str:
    """1234.5 -> '1234,50' (decimal com vírgula, sem separador de milhar)."""
    return f"{valor:.{casas}f}".replace(".", ",")


def gerar_linhas(n: int, semente: int = 42) -> list[list[str]]:
    rnd = random.Random(semente)
    linhas = []
    for i in range(n):
        ativo = rnd.random() < 0.8
        mes_desl = 0 if ativo else rnd.randint(1, 12)
        remun = round(rnd.uniform(900, 9000), 2)
        linha = [
            rnd.choice(MUNICIPIOS), rnd.choice(CNAES), rnd.choice(CBOS), "1" if ativo else "0",
            str(rnd.choice([1, 2])), str(rnd.randint(1, 11)), str(rnd.choice([1, 2, 4, 6, 8, 9])),
            str(rnd.randint(16, 70)), _br(rnd.uniform(1, 240), 1), str(mes_desl),
            "0" if ativo else str(rnd.choice([11, 12, 21])), str(rnd.randint(1, 10)), "2062",
            _br(remun), _br(remun * 0.95),
            _br(remun / SALARIO_MINIMO), _br(remun * 0.95 / SALARIO_MINIMO),
        ]
        # Valores inválidos de propósito, para exercitar a silver (Aula 12)
        if i % 199 == 0:
            linha[0] = "9999"            # município inválido -> cod_uf NULL (~0,5%)
        if i % 89 == 0:
            linha[7] = "150"             # idade implausível -> NULL
        if i % 83 == 0:
            linha[1] = "4711"            # CNAE com 4 dígitos -> NULL
        if i % 101 == 0:
            linha[13] = "{ñ class}"      # remuneração ignorada -> NULL
        linhas.append(linha)
    return linhas


def escrever_txt(destino: Path, n: int, semente: int = 42) -> Path:
    destino.mkdir(parents=True, exist_ok=True)
    arquivo = destino / NOME_ARQUIVO
    with arquivo.open("w", encoding="latin-1", newline="") as f:
        f.write(";".join(CABECALHO) + "\n")
        for linha in gerar_linhas(n, semente):
            f.write(";".join(linha) + "\n")
    return arquivo


def escrever_7z(destino: Path, n: int, semente: int = 42) -> Path:
    import tempfile

    import py7zr

    destino.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        txt = escrever_txt(Path(tmp), n, semente)
        alvo = destino / "RAIS_VINC_PUB_SINTETICO.7z"
        with py7zr.SevenZipFile(alvo, "w") as z:
            z.write(txt, arcname=txt.name)
    return alvo


def main() -> None:
    p = argparse.ArgumentParser(description="Amostra SINTÉTICA no formato RAIS")
    p.add_argument("--saida", required=True, type=Path)
    p.add_argument("--linhas", type=int, default=500)
    p.add_argument("--semente", type=int, default=42)
    p.add_argument("--7z", dest="compactar", action="store_true", help="gera .7z em vez de .txt")
    args = p.parse_args()
    fn = escrever_7z if args.compactar else escrever_txt
    print(f"[amostra SINTÉTICA] {fn(args.saida, args.linhas, args.semente)}")


if __name__ == "__main__":
    main()
