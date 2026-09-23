# case_pp

![CI](https://github.com/FelipeMDuarte/case_pp/actions/workflows/ci.yml/badge.svg)

API em FastAPI + Pydantic + MongoDB (Motor async), com Docker Compose para orquestrar a API e o banco.

## Pontos de Evolução do Projeto

### PATCH em vez de PUT
Mais adequado pra atualização parcial, PUT obrigaria reenviar a entidade inteira.

### Modelagem 100% em Mongo não é ideal
  Relacionamentos ficariam mais naturais em SQL; NoSQL faz mais sentido pras tabelas de histórico/auditoria.

### Segurança (auth/autorização)
  Deixada de fora por ser um case, mas seria obrigatória em produção.

### Consistência/atomicidade
  audit_event e schema_version são escritos em chamadas separadas depois do write principal, se o processo cair no meio, perde o rastro de auditoria.
  Pediria transação multi-documento (replica set) ou padrão outbox.

### Busca com filtro 
  Lê a coleção inteira pra RAM antes de filtrar não escala com volume real, produção pediria melhora/mudança.

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

Dev (`docker-compose.yml` — Mongo exposto em `localhost:27017`):

```bash
docker compose up --build
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

`.github/workflows/ci.yml` roda lint (`ruff`) e os testes a cada push/PR na `main` — o mesmo que rodar localmente, só que automático.

## Logging

Todo request gera um `request_id` (reaproveita o header `X-Request-ID` se o cliente já mandar um, senão gera um novo) e loga início, fim com status/duração, e o traceback completo se algo não tratado quebrar no meio — tudo com esse mesmo id, pra dar pra achar todas as linhas de um request específico no log. Nível `DEBUG` com `DEBUG=true`, `INFO` por padrão. O access log padrão do uvicorn fica desligado (`--no-access-log`) porque esse middleware já cobre a mesma informação com mais contexto.

## Endpoints

| Método | Rota                    | Descrição                                          |
|--------|--------------------------|-----------------------------------------------------|
| POST   | `/metadata`              | Cria um metadado (também loga `audit_event` e, se tiver `structure`, `schema_version`); `409` se a `urn` já existir |
| GET    | `/metadata`               | Lista metadados; aceita qualquer campo como busca parcial (`?asset.name=compras&source.platform=postgresql`) |
| GET    | `/metadata/{id}`          | Busca por id                                        |
| PATCH  | `/metadata/{id}`          | Atualiza parcialmente (também loga `audit_event`, e `schema_version` se mudar `structure`) |
| DELETE | `/metadata/{id}`          | Soft delete: seta `asset.status = "DEPRECATED"`, o registro continua existindo (também loga um `audit_event`) |
| POST   | `/data_flows`             | Cria uma relação de fluxo entre dois metadados; `422` se `source_urn`/`target_urn` não existirem, `409` se o par já existir |
| GET    | `/data_flows`             | Lista fluxos                                        |
| GET    | `/data_flows/{id}`        | Busca por id                                        |
| PATCH  | `/data_flows/{id}`        | Atualiza parcialmente                                |
| DELETE | `/data_flows/{id}`        | Remove                                              |
| GET    | `/audit_events`           | Lista eventos de auditoria (somente leitura)        |
| GET    | `/audit_events/{id}`      | Busca por id                                        |
| GET    | `/schema_versions`        | Lista o histórico de estrutura dos metadados (somente leitura) |
| GET    | `/schema_versions/{id}`   | Busca por id                                        |
| GET    | `/health`                 | Liveness — só confirma que a API está de pé, não depende do Mongo |
| GET    | `/health/database`        | Readiness — dá `ping` no Mongo de verdade; `503` se não responder |

Todo `GET` de lista devolve um envelope de paginação, não um array solto: `{"items": [...], "total": N, "skip": 0, "limit": 100}`.
