<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# [Apêndice C](apendice-c.md) — Glossário

- **ACID:** atomicidade, consistência, isolamento e durabilidade. Garante que uma transação acontece inteira ou não acontece.
- **AQE:** *Adaptive Query Execution*. O Spark reotimiza o plano durante a execução.
- **Bind mount:** pasta do host montada no container.
- **Broadcast join:** join em que a tabela pequena é copiada para todas as tarefas, sem shuffle.
- **Data skew:** dados concentrados em poucas chaves, gerando tarefas desbalanceadas.
- **Idempotência:** executar várias vezes produz o mesmo resultado.
- **Lazy evaluation:** transformações só executam quando há uma ação.
- **Medallion:** organização em bronze, silver e gold.
- **Partition pruning:** ler só as partições exigidas pelo filtro.
- **S3A:** conector Hadoop/Spark para storage compatível com S3.
- **Schema enforcement / evolution:** recusar ou aceitar mudanças de schema na escrita.
- **Shuffle:** redistribuição de dados entre partições; é a operação mais cara do Spark.
- **Spill:** dados despejados em disco quando não cabem na memória.
- **Time travel:** ler uma versão antiga de uma tabela Delta.
- **Vínculo:** relação de emprego registrada; é a unidade de uma linha na RAIS.
