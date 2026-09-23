# case_pp

![CI](https://github.com/FelipeMDuarte/case_pp/actions/workflows/ci.yml/badge.svg)

API em FastAPI + Pydantic + MongoDB (Motor async), com Docker Compose para orquestrar a API e o banco.

## Escolhas de implementação

### PATCH em vez de PUT
 Mais adequado pra atualização parcial, PUT obrigaria reenviar a entidade inteira.

### Busca por URN
  É possível mas depende um pouco de escolhas do time sobre arquitetura e bancos

### Busca por filtro é exata, não parcial
  Filtro vira query nativa do Mongo (dot-notation direto, `?asset.status=ACTIVE`), case-sensitive. Paginação e contagem são nativas do Mongo em qualquer busca, com ou sem filtro.

### Filtro sem whitelist nem conversão de tipo
  Qualquer campo do payload vira filtro, mas chega como string, então campo booleano/numérico (`active`, `quality.score`, `contains_personal_data`) nunca bate, e campo inexistente (`?typo=x`) devolve 200 com lista vazia em vez de erro. 
  Bloqueei a parte perigosa, chave com `$`, que virava operador do Mongo. 
  O resto pediria uma whitelist de campos filtráveis derivada do modelo, convertendo o tipo certo por campo.

## Pontos de Evolução do Projeto

### Modelagem 100% em Mongo não é ideal
  Relacionamentos ficariam mais naturais em SQL; NoSQL faz mais sentido pras tabelas de histórico/auditoria.

### Segurança (auth/autorização)
  Deixada de fora por ser um case, mas seria obrigatória em produção.

### CORS
  Não tem mas seria a primeira adição caso a API vá ser acessada por frontend

### Consistência/atomicidade
  audit_event e schema_version são escritos em chamadas separadas depois do write principal, se o processo cair no meio, perde o rastro de auditoria.
  Pediria transação multi-documento (replica set) ou padrão outbox.

### Versionamento de API
  Seria feito conforme necessário via prefix no include_router do FastAPI

## Estrutura

```
app/
  models/            # Schemas Pydantic por recurso (metadata, data_flow, audit_event)
  connectors/
    mongo_con.py     # MongoConnector genérico
  api/
    crud.py          # factories de router (build_read_only_router, build_crud_router)
    utils.py         # efeitos colaterais das escritas (audit_events, schema_versions) e busca
    routers.py       # monta os routers de cada recurso e expõe all_routers
  logging_config.py  # configuração de logging + request-id por request
  middleware.py       # middleware http que loga cada request (usa logging_config)
...
...
.env.example                # variáveis dev
.env.prod.example           # variáveis prod
METADATA.md                 # modelo de dados
metadata_sample.json        # exemplo das 3 coleções
scripts/
  seed.py                    # popula a API com o exemplo acima
```

Em `METADATA.md` temos o modelo de dados completo (`metadata`, `data_flows`, `audit_events`, `schema_versions`).

## Rodando com Docker

Dev (`docker-compose.yml`, Mongo exposto em `localhost:27017`):

```bash
docker compose up -d --build
docker compose logs -f api   # só o log da API, sem o log do Mongo junto
```

Prod (`docker-compose.prod.yml` sem publicar a porta do Mongo):

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

A API sobe em `http://localhost:8000` (docs em `/docs`) nos dois casos.

## Populando com dados de exemplo

Com a API no ar (Docker ou local), rode em outro terminal:

```bash
.venv/bin/python3 scripts/seed.py
```

O script lê `metadata_sample.json` e faz `POST` em `/metadata` e `/data_flows` pelos endpoints reais da API, então os `audit_events` correspondentes são gerados sozinhos, como consequência normal do `POST`, sem precisar inserir manualmente.

## Rodando localmente (sem Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# suba um mongo local (ou use docker compose up mongo)
uvicorn app.main:app --reload --no-access-log
```

## Testes

Os testes usam `mongomock-motor` para simular o Mongo, não é necessário um banco real:

```bash
pytest
```

Cobertura:

```bash
pytest --cov=app --cov-report=term-missing
```

Lint (`ruff`, config em `pyproject.toml`):

```bash
ruff check .
```

## CI

`.github/workflows/ci.yml` roda lint (`ruff`) e os testes a cada push/PR na `main`, o mesmo que rodar localmente, só que automático.

## Logging

Todo request gera um `request_id` e loga início, fim com status/duração, e o traceback completo se algo não tratado quebrar no meio, tudo com esse mesmo id, pra dar pra achar todas as linhas de um request específico no log.

## Endpoints

| Método | Rota                    | Descrição                                          |
|--------|--------------------------|-----------------------------------------------------|
| POST   | `/metadata`              | Cria um metadado (também loga `audit_event` e, se tiver `structure`, `schema_version`); `409` se a `urn` já existir |
| GET    | `/metadata`               | Lista metadados; aceita qualquer campo como filtro exato, case-sensitive (`?asset.status=ACTIVE&source.platform=BIGQUERY`) |
| GET    | `/metadata/{id}`          | Busca por id                                        |
| PATCH  | `/metadata/{id}`          | Atualiza parcialmente (também loga `audit_event`, e `schema_version` se mudar `structure`) |
| DELETE | `/metadata/{id}`          | Soft delete: seta `asset.status = "DEPRECATED"`, o registro continua existindo (também loga um `audit_event`); `410` se já estava deprecado |
| POST   | `/data_flows`             | Cria uma relação de fluxo entre dois metadados; `422` se `source_urn`/`target_urn` não existirem, `409` se o par já existir |
| GET    | `/data_flows`             | Lista fluxos                                        |
| GET    | `/data_flows/{id}`        | Busca por id                                        |
| PATCH  | `/data_flows/{id}`        | Atualiza parcialmente                                |
| DELETE | `/data_flows/{id}`        | Remove                                              |
| GET    | `/audit_events`           | Lista eventos de auditoria (somente leitura)        |
| GET    | `/audit_events/{id}`      | Busca por id                                        |
| GET    | `/schema_versions`        | Lista o histórico de estrutura dos metadados (somente leitura) |
| GET    | `/schema_versions/{id}`   | Busca por id                                        |
| GET    | `/health`                 | Liveness: só confirma que a API está de pé, não depende do Mongo |
| GET    | `/health/database`        | Readiness: dá `ping` no Mongo de verdade; `503` se não responder |

Todo `GET` de lista devolve um envelope de paginação, não um array solto: `{"items": [...], "total": N, "skip": 0, "limit": 100}`.
