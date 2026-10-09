<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# [Apêndice D](apendice-d.md) — Próximos passos

1. **RAIS Estabelecimentos:** some a segunda base e pratique joins grandes e skew.
2. **`MERGE` no Delta:** pratique *upserts* com uma tabela de correções.
3. **Iceberg:** recrie a gold em Iceberg com catálogo REST e compare a experiência.
4. **Consulta SQL:** suba o **Trino** no Compose para consultar o lake por SQL.
5. **Orquestração:** agende o pipeline com **Airflow** ou **Dagster** no mesmo Compose.
6. **Visualização:** suba **Metabase** ou **Superset** no Compose e conecte à gold.
7. **Cluster:** transforme o serviço `spark` em master + workers (Spark standalone) e observe o que muda no tuning.

---

## Checklist final

- [ ] Repositório criado, `.gitignore` e `.env.example` versionados, `.env` fora do Git
- [ ] `make up` sobe minio, minio-init (exit 0) e spark
- [ ] `make smoke` passa
- [ ] Parte [5](parte-05.md) concluída (exercícios de fundamentos)
- [ ] Dicionário baixado e `docs/dicionario.md` preenchido
- [ ] Bronze, silver e gold gravadas em Delta no MinIO
- [ ] Contagem silver = bronze e checagens passando
- [ ] Reprocessar um ano não duplica dados
- [ ] Time travel, `OPTIMIZE` e schema enforcement testados
- [ ] Benchmark feito e configuração padrão registrada em `docs/decisoes.md`
- [ ] Testes, lint e CI verdes
- [ ] README com arquitetura, decisões, resultados e limitações
