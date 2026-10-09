<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# [Apêndice A](apendice-a.md) — Armadilhas conhecidas

1. **O schema muda entre anos.** Por isso a bronze é toda string com `mergeSchema`, e há `col_or_null` e `OBRIGATORIAS`.
2. **eSocial a partir do ano-base 2019.** A forma de declaração mudou gradualmente por grupos de empresas, o que pode afetar comparações históricas. Leia as notas técnicas de cada ano.
3. **Versão parcial × final.** Alguns anos tiveram divulgação parcial antes da final. Use a final e registre a escolha.
4. **Arquivo "NI".** São os não identificados. Inclua-o para ter o total nacional; ele não tem UF válida.
5. **"Ignorado" varia por coluna** (`-1`, `0`, `{ñ class}`). Decida coluna a coluna e documente.
6. **Zeros à esquerda.** CBO, CNAE e município são **string**.
7. **Nominal × salário mínimo.** Para série histórica, use `*_sm`.
8. **Vínculo ≠ pessoa.** Uma pessoa pode ter vários vínculos.
9. **Disco.** Apague `raw` após a bronze (`--limpar-raw`) e monitore o volume do MinIO.
10. **Encoding.** Se `Município` aparecer como `Munic�pio`, o encoding está errado.
