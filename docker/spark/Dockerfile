# Origem: Guia Parte 4.4 / Aula 02
# 1) Base: Python sobre Debian 12 (bookworm), que tem o OpenJDK 17 no repositório
FROM python:3.11-slim-bookworm

# 2) Versões como ARG: muda num lugar só
ARG HADOOP_AWS_VERSION=3.3.4
ARG AWS_SDK_VERSION=1.12.262
ARG DELTA_VERSION=3.2.0
ARG SCALA_VERSION=2.12
ARG HOST_UID=1000

# 3) Pacotes do sistema (muda pouco -> fica no topo para aproveitar o cache)
RUN apt-get update \
 && apt-get install -y --no-install-recommends openjdk-17-jre-headless curl procps git \
 && rm -rf /var/lib/apt/lists/*

# 4) Dependências Python (antes do código, para aproveitar o cache)
COPY requirements.txt requirements-dev.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt -r /tmp/requirements-dev.txt

# 5) JARs do Delta e do S3A dentro da pasta de JARs do PySpark
#    (assim o Spark os carrega sozinho, sem internet em tempo de execução)
RUN SPARK_JARS="$(python -c 'import os, pyspark; print(os.path.join(os.path.dirname(pyspark.__file__), "jars"))')" \
 && MAVEN=https://repo1.maven.org/maven2 \
 && curl -fsSL -o "$SPARK_JARS/hadoop-aws-${HADOOP_AWS_VERSION}.jar" \
      "$MAVEN/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar" \
 && curl -fsSL -o "$SPARK_JARS/aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar" \
      "$MAVEN/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_VERSION}/aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar" \
 && curl -fsSL -o "$SPARK_JARS/delta-spark_${SCALA_VERSION}-${DELTA_VERSION}.jar" \
      "$MAVEN/io/delta/delta-spark_${SCALA_VERSION}/${DELTA_VERSION}/delta-spark_${SCALA_VERSION}-${DELTA_VERSION}.jar" \
 && curl -fsSL -o "$SPARK_JARS/delta-storage-${DELTA_VERSION}.jar" \
      "$MAVEN/io/delta/delta-storage/${DELTA_VERSION}/delta-storage-${DELTA_VERSION}.jar"

# 6) Usuário sem privilégios de root (segurança).
#    O UID igual ao do seu usuário no host evita problemas de permissão no bind mount.
RUN useradd -m -u "${HOST_UID}" app \
 && mkdir -p /app /staging /tmp/spark \
 && chown -R app:app /app /staging /tmp/spark

# 7) [Complemento da plataforma] Magic %%sql nos notebooks (células SQL como no Databricks)
COPY --chown=app:app docker/spark/ipython_sql.py /home/app/.ipython/profile_default/startup/00-sql.py

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

WORKDIR /app
USER app

EXPOSE 8888 4040 8000
CMD ["bash"]
