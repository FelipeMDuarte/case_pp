# case_pp

API em FastAPI + Pydantic + MongoDB (Motor async), com Docker Compose para orquestrar a API e o banco.

## Estrutura

```
app/
  models/            # Schemas Pydantic por recurso (metadata, data_flow, audit_event)
  connectors/
    mongo_con.py     # MongoConnector genérico
  api/
    crud.py          # factory de CRUD genérico
    routers.py       # monta os routers de cada recurso e expõe all_routers
...
...
.env.example                # variáveis dev
.env.prod.example           # variáveis prod
METADATA.md                 # modelo de dados
metadata_sample.json        # exemplo das 3 coleções
scripts/
  seed.py                    # popula a API com o exemplo acima
```

Em `METADATA.md` temos o modelo de dados completo (`metadata`, `data_flows`, `audit_events`).

## Rodando com Docker

Dev (`docker-compose.yml` Mongo exposto em `localhost:27017`):

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

O script lê `metadata_sample.json` e faz `POST` em `/metadata` e `/data_flows` pelos endpoints reais da API — então os `audit_events` correspondentes são gerados sozinhos, como consequência normal do `POST`, sem precisar inserir manualmente. 

## Rodando localmente (sem Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# suba um mongo local (ou use docker compose up mongo)
uvicorn app.main:app --reload
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

## Endpoints

| Método | Rota                    | Descrição                                          |
|--------|--------------------------|-----------------------------------------------------|
| POST   | `/metadata`              | Cria um metadado (também loga um `audit_event`)     |
| GET    | `/metadata`               | Lista metadados                                     |
| GET    | `/metadata/{id}`          | Busca por id                                        |
| PATCH  | `/metadata/{id}`          | Atualiza parcialmente (também loga um `audit_event`)|
| DELETE | `/metadata/{id}`          | Remove (também loga um `audit_event`)               |
| POST   | `/data_flows`             | Cria uma relação de fluxo entre dois metadados      |
| GET    | `/data_flows`             | Lista fluxos                                        |
| GET    | `/data_flows/{id}`        | Busca por id                                        |
| PATCH  | `/data_flows/{id}`        | Atualiza parcialmente                                |
| DELETE | `/data_flows/{id}`        | Remove                                              |
| GET    | `/audit_events`           | Lista eventos de auditoria (somente leitura)        |
| GET    | `/audit_events/{id}`      | Busca por id                                        |
| GET    | `/health`                 | Healthcheck                                         |
