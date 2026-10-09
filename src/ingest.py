"""Download e extração dos microdados da RAIS.

Origem: Guia Parte 8.2 / Aula 11.
"""
import ftplib
from pathlib import Path

import py7zr

from config.settings import LANDING, RAW

# CONFIRME o endereço atual na página de microdados do MTE: ele já mudou no passado.
FTP_HOST = "ftp.mtps.gov.br"
FTP_PATH = "/pdet/microdados/RAIS/{ano}/"


def baixar(ano: int, filtro: str = "VINC") -> list[Path]:
    """Baixa os .7z de vínculos de um ano para landing/<ano>/ (pula os já baixados)."""
    destino = LANDING / str(ano)
    destino.mkdir(parents=True, exist_ok=True)
    baixados: list[Path] = []

    with ftplib.FTP(FTP_HOST, timeout=120) as ftp:
        ftp.login()
        ftp.cwd(FTP_PATH.format(ano=ano))
        for nome in ftp.nlst():
            if filtro not in nome.upper() or not nome.lower().endswith(".7z"):
                continue
            arquivo = destino / nome
            if arquivo.exists():
                print(f"[skip] {nome}")
            else:
                print(f"[baixando] {nome}")
                parcial = arquivo.with_suffix(".part")
                with open(parcial, "wb") as f:
                    ftp.retrbinary(f"RETR {nome}", f.write)
                parcial.rename(arquivo)          # só "existe" quando terminou
            baixados.append(arquivo)
    return baixados


def extrair(ano: int) -> Path:
    """Extrai todos os .7z de landing/<ano>/ para raw/<ano>/."""
    origem, destino = LANDING / str(ano), RAW / str(ano)
    destino.mkdir(parents=True, exist_ok=True)

    arquivos = sorted(origem.glob("*.7z"))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum .7z em {origem}")

    for arq in arquivos:
        print(f"[extraindo] {arq.name}")
        with py7zr.SevenZipFile(arq, "r") as z:
            z.extractall(path=destino)
    return destino


if __name__ == "__main__":
    import sys

    extrair(int(sys.argv[1]))
