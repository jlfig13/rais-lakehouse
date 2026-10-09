<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# Parte [1](parte-01.md) — Arquitetura e decisões

## 1.1 Visão geral { #parte-1-1 }

```
                    ┌──────────────────────── docker compose ────────────────────────┐
                    │                                                                 │
  gov.br (.7z) ───▶ │  container "spark"                     container "minio"        │
                    │  ┌───────────────────────────┐        ┌───────────────────────┐ │
                    │  │ Python + Java + PySpark   │  S3A   │ bucket "rais"          │ │
                    │  │ + Delta + JupyterLab      │ ─────▶ │  bronze/ (Delta)       │ │
                    │  │                           │        │  silver/ (Delta)       │ │
                    │  │ /staging (disco local):   │        │  gold/   (Delta)       │ │
                    │  │   landing/ (.7z)          │        └───────────────────────┘ │
                    │  │   raw/ (.txt temporário)  │                                   │
                    │  └───────────────────────────┘        container "minio-init"    │
                    │                                       (cria bucket e usuário)   │
                    └─────────────────────────────────────────────────────────────────┘
```

## 1.2 Camadas (arquitetura medallion) { #parte-1-2 }

| Camada | Onde fica | Formato | Objetivo | Regra de ouro |
|---|---|---|---|---|
| **landing** | disco local (`/staging/landing`) | `.7z` original | Guardar o arquivo como veio | Nunca editar; é a fonte da verdade |
| **raw** | disco local (`/staging/raw`) | `.txt` extraído | Arquivo intermediário | Temporário; apague após a bronze |
| **bronze** | MinIO | Delta | Cópia fiel e eficiente da origem | Tudo `string`, nomes normalizados, sem regra de negócio |
| **silver** | MinIO | Delta | Dado limpo e tipado | Uma linha = um vínculo, tipos corretos |
| **gold** | MinIO | Delta | Respostas prontas para análise | Cada tabela responde uma pergunta |

## 1.3 Decisões de arquitetura { #parte-1-3 }

Registre decisões assim (formato **ADR**, *Architecture Decision Record*) em `docs/decisoes.md`. É uma prática muito valorizada em projetos de portfólio.

| # | Decisão | Escolha | Alternativa considerada | Motivo |
|---|---|---|---|---|
| 1 | Execução | Spark em modo `local` num container | Cluster Spark standalone | Uma máquina basta para aprender; o código é o mesmo num cluster |
| 2 | Orquestração de infraestrutura | Docker Compose | Instalar tudo no host | Reprodutível: qualquer pessoa sobe o projeto com um comando |
| 3 | Armazenamento | MinIO (API S3) | HDFS, disco local | API S3 é padrão de mercado; o código migra para qualquer S3 |
| 4 | Formato de tabela | **Delta Lake** | Apache Iceberg | Setup mais simples no PySpark (sem catálogo); mesmos conceitos |
| 5 | Staging | Disco local | MinIO | `.7z`/`.txt` são temporários; não precisam de versionamento |
| 6 | JARs | Embutidos na imagem | Baixar do Maven em tempo de execução | Funciona sem internet e é reprodutível |

**Delta × Iceberg, em resumo:** os dois oferecem ACID, *time travel*, `MERGE` e evolução de schema. O Delta exige só JARs e duas configurações no Spark. O Iceberg exige configurar um **catálogo** (REST, JDBC, Hive ou Hadoop) desde o início e brilha quando vários engines (Trino, Flink, Spark) leem as mesmas tabelas. Aprendendo Delta, migrar depois é tranquilo.

---
