COMPOSE := docker compose
ANOS    ?= 2022
ETAPAS  ?= extrair bronze silver gold catalogo
AULA    ?= 01
ANO     ?= 2022

.PHONY: help up down logs ps shell smoke pipeline test lint fmt check check-host progresso curso catalogo

help:            ## lista os comandos
	@grep -E '^[a-z-]+:.*##' Makefile | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

up:              ## constrói e sobe a infraestrutura
	$(COMPOSE) up -d --build

down:            ## para e remove containers (mantém os dados)
	$(COMPOSE) down

logs:            ## acompanha os logs
	$(COMPOSE) logs -f

ps:              ## estado dos containers
	$(COMPOSE) ps -a

shell:           ## terminal dentro do container spark
	$(COMPOSE) exec spark bash

smoke:           ## teste de fumaça (Spark + Delta + MinIO)
	$(COMPOSE) exec spark python -m scripts.smoke_test

pipeline:        ## roda o pipeline. Ex.: make pipeline ANOS="2021 2022"
	$(COMPOSE) exec spark python -m src.run_pipeline --anos $(ANOS) --etapas $(ETAPAS) --limpar-raw

test:            ## testes de unidade (tests/)
	$(COMPOSE) exec spark pytest -q

lint:            ## análise estática
	$(COMPOSE) exec spark ruff check .

fmt:             ## formata o código
	$(COMPOSE) exec spark ruff format .

check:           ## valida uma aula no container. Ex.: make check AULA=11 ANO=2022
	$(COMPOSE) exec spark pytest -v -p no:cacheprovider labcheck/test_aula$(AULA).py --ano $(ANO)

check-host:      ## valida aulas 01-05 no host. Ex.: make check-host AULA=03
	.venv-host/bin/pytest -v -p no:cacheprovider $(firstword $(wildcard labcheck/host/test_aula$(AULA).py labcheck/test_aula$(AULA).py))

progresso:       ## gera curso/docs/progresso.md a partir do histórico
	$(COMPOSE) exec spark python -m scripts.gerar_progresso

curso:           ## regenera as páginas e sobe o site em http://localhost:8000
	$(COMPOSE) exec spark python -m scripts.gerar_curso
	$(COMPOSE) up -d curso

catalogo:        ## valida o catálogo, grava as descrições nas tabelas e gera catalogo/rais.json
	$(COMPOSE) exec spark python -m src.catalogo --aplicar
