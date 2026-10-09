<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# Guia original — RAIS Lakehouse — PySpark + Delta Lake + MinIO com Docker Compose

Guia educacional e roteiro de um projeto de GitHub. Você vai construir, do zero, um *lakehouse* on-premises e 100% open source que processa os microdados da **RAIS** (2019 até o último ano-base publicado) nas camadas **bronze → silver → gold**.

**O que você vai aprender**
- **Docker e Docker Compose:** imagem, container, volume, rede, variáveis de ambiente.
- **PySpark:** DataFrame, transformações, agregações, joins, window functions, *lazy evaluation*, partições.
- **Delta Lake:** transações ACID, versionamento, *time travel*, schema enforcement, `OPTIMIZE` e `VACUUM`.
- **MinIO:** object storage compatível com S3, buckets, credenciais e políticas de acesso.
- **Engenharia de dados:** arquitetura medallion, idempotência, qualidade de dados e tuning do Spark.
- **Projeto profissional:** estrutura de repositório, testes, lint, CI no GitHub Actions, commits e README.

**Como usar este guia**
- Cada parte segue a mesma sequência: **Conceito** (o que e por quê), **Sintaxe/Prática** (o que fazer) e **Checkpoint** (como saber que deu certo).
- Siga na ordem e faça um commit ao fim de cada parte (a Parte [3](parte-03.md) explica como).
- Comece com **1 ano e 1 região** (ex.: 2022 + Nordeste) e só escale na Parte [12](parte-12.md).

> ⚠️ **Pontos que você precisa confirmar por conta própria**, porque mudam com o tempo e eu não consigo verificá-los no seu ambiente:
> 1. **Nomes de colunas e códigos da RAIS** de cada ano. Confira no dicionário oficial (Parte [6](parte-06.md)). O código foi escrito para falhar com mensagem clara se faltar algo.
> 2. **Imagem Docker do MinIO.** O projeto mudou a forma de distribuição da edição *community* em 2025. Confira no repositório oficial qual imagem e tag usar (Parte [4](parte-04.md)).
> 3. **Compatibilidade de versões** entre PySpark, Delta e hadoop-aws (Parte [4](parte-04.md)).
> 4. **URL de download** dos microdados (Parte [8](parte-08.md)).

---


## Sumário

- [Parte [1](parte-01.md) — Arquitetura e decisões](parte-01.md)
- [Parte [2](parte-02.md) — Conceitos de Docker e Docker Compose](parte-02.md)
- [Parte [3](parte-03.md) — Estrutura do repositório e Git](parte-03.md)
- [Parte [4](parte-04.md) — Infraestrutura: Dockerfile, Compose e MinIO](parte-04.md)
- [Parte [5](parte-05.md) — Fundamentos de PySpark](parte-05.md)
- [Parte [6](parte-06.md) — Conhecendo a RAIS](parte-06.md)
- [Parte [7](parte-07.md) — Código base: configuração e utilitários](parte-07.md)
- [Parte [8](parte-08.md) — Ingestão (landing → raw)](parte-08.md)
- [Parte [9](parte-09.md) — Bronze](parte-09.md)
- [Parte [10](parte-10.md) — Silver](parte-10.md)
- [Parte [11](parte-11.md) — Gold](parte-11.md)
- [Parte [12](parte-12.md) — Pipeline completo (2019 → hoje)](parte-12.md)
- [Parte [13](parte-13.md) — Delta Lake na prática](parte-13.md)
- [Parte [14](parte-14.md) — Tuning: threads, memória e partições](parte-14.md)
- [Parte [15](parte-15.md) — Qualidade, testes e CI](parte-15.md)
- [Parte [16](parte-16.md) — Boas práticas de GitHub](parte-16.md)
- [[Apêndice A](apendice-a.md) — Armadilhas conhecidas](apendice-a.md)
- [[Apêndice B](apendice-b.md) — Solução de problemas](apendice-b.md)
- [[Apêndice C](apendice-c.md) — Glossário](apendice-c.md)
- [[Apêndice D](apendice-d.md) — Próximos passos](apendice-d.md)
