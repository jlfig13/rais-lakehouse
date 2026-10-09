<!-- Página GERADA de docs/guia/rais-lakehouse-guia.md -->

# [Apêndice B](apendice-b.md) — Solução de problemas

| Sintoma | Causa provável | Solução |
|---|---|---|
| `minio-init` termina com erro | Credenciais ou sintaxe do `mc` | `docker compose logs minio-init`; ajuste o script à versão do `mc` |
| `spark` não sobe | `minio-init` falhou (dependência) | Resolva o `minio-init` primeiro |
| `Connection refused` ao acessar o MinIO | Usou `localhost` dentro do container | Use `http://minio:9000` |
| `ClassNotFoundException: S3AFileSystem` | JAR não baixou no build | Refaça com `docker compose build --no-cache spark` |
| `403` / `InvalidAccessKeyId` | Usuário da aplicação não criado ou sem política | Veja o log do `minio-init`; confira `APP_ACCESS_KEY` |
| `UnknownHostException: rais.minio` | Faltou path-style | `fs.s3a.path.style.access=true` |
| `Permission denied` em `/app` ou `/staging` | UID diferente entre host e container | Ajuste `HOST_UID` (`id -u`) e reconstrua |
| Container morre com código 137 | `mem_limit` estourado | Reduza `SPARK_MEM` ou aumente `CONTAINER_MEM` |
| `OutOfMemoryError` | Heap da JVM pequeno | Menos threads ou mais `SPARK_MEM` |
| Spark UI não abre | Sem sessão ativa ou porta errada | A UI só existe enquanto há sessão; tente 4041 |
| `make` reclama de "missing separator" | Espaços no lugar de TAB no Makefile | Use TAB |
