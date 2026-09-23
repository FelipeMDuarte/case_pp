# Requisições de exemplo

JSONs prontos pra colar no Postman ou no "Try it out" do Swagger (`/docs`), cobrindo todas as rotas da API. Os exemplos abaixo são um cenário coerente, os mesmos `urn` se repetem entre `metadata` e `data_flows`, então seguir a ordem funciona de ponta a ponta.

Onde aparecer `{id}`, troque pelo `id` que veio na resposta do `POST` correspondente (o Mongo gera um novo a cada vez).

Todo `GET` de lista devolve um envelope, não um array solto: `{"items": [...], "total": N, "skip": 0, "limit": 100}`.

## `metadata`

### `POST /metadata`: tabela de origem (Postgres)

```json
{
  "urn": "urn:data:postgresql:commerce-prod.public.orders",
  "asset": {
    "name": "orders",
    "display_name": "Pedidos (operacional)",
    "description": "Tabela transacional do sistema de vendas.",
    "asset_type": "TABLE",
    "environment": "PRODUCTION",
    "status": "ACTIVE",
    "domain": "SALES",
    "layer": "BRONZE",
    "tags": ["orders"]
  },
  "source": {
    "platform": "POSTGRESQL",
    "fully_qualified_name": "commerce-prod.public.orders"
  },
  "business_metadata": {
    "purpose": "Registrar pedidos no momento da compra.",
    "grain": "Uma linha por pedido."
  },
  "ownership": {
    "technical_owner": {
      "type": "TEAM",
      "name": "Data Engineering",
      "contact": "data-engineering@example.com"
    }
  },
  "security_and_privacy": {
    "sensitivity": "CONFIDENTIAL",
    "contains_personal_data": true,
    "regulations": ["LGPD"]
  }
}
```

### `POST /metadata`: tabela de destino (BigQuery, com `structure` e `quality`)

Como tem `structure`, esse `POST` também gera uma versão em `schema_versions` sozinho.

```json
{
  "urn": "urn:data:bigquery:company-analytics-prod.sales.orders",
  "asset": {
    "name": "orders",
    "display_name": "Pedidos",
    "description": "Tabela analítica com um registro por pedido.",
    "asset_type": "TABLE",
    "environment": "PRODUCTION",
    "status": "ACTIVE",
    "domain": "SALES",
    "layer": "GOLD",
    "tags": ["orders", "revenue"]
  },
  "source": {
    "platform": "BIGQUERY",
    "fully_qualified_name": "company-analytics-prod.sales.orders"
  },
  "business_metadata": {
    "purpose": "Disponibilizar pedidos para análises de receita.",
    "grain": "Uma linha por pedido."
  },
  "ownership": {
    "business_owner": {
      "type": "TEAM",
      "name": "Sales Operations",
      "contact": "sales-operations@example.com"
    },
    "technical_owner": {
      "type": "TEAM",
      "name": "Data Engineering",
      "contact": "data-engineering@example.com"
    }
  },
  "security_and_privacy": {
    "sensitivity": "CONFIDENTIAL",
    "contains_personal_data": true,
    "regulations": ["LGPD"]
  },
  "quality": {
    "status": "PASSED",
    "score": 0.97,
    "checked_at": "2026-09-18T09:45:00Z",
    "issues": []
  },
  "structure": {
    "columns": [
      { "name": "order_id", "data_type": "STRING", "description": "Identificador único do pedido." },
      { "name": "gross_amount", "data_type": "NUMERIC", "description": "Valor bruto do pedido." }
    ]
  }
}
```

### `GET /metadata`: lista tudo

Sem corpo. `GET /metadata`

### `GET /metadata`: busca exata, case-sensitive

Sem corpo, só query params. Qualquer campo vira filtro, inclusive aninhado. A comparação é exata e case-sensitive:

```
GET /metadata?asset.domain=SALES
GET /metadata?asset.status=ACTIVE&source.platform=BIGQUERY
GET /metadata?skip=0&limit=10
```

### `GET /metadata/{id}`: busca por id

Sem corpo. `GET /metadata/{id}`

### `PATCH /metadata/{id}`: atualização parcial

Só muda `sensitivity`; `contains_personal_data`/`regulations` continuam como estavam (merge de verdade, não substitui a seção inteira).

```json
{
  "security_and_privacy": {
    "sensitivity": "RESTRICTED"
  }
}
```

### `PATCH /metadata/{id}`: atualização parcial de bloco com campo obrigatório

`asset` tem campos obrigatórios (`name`, `asset_type`, `environment`), mesmo assim o merge parcial funciona, não precisa reenviar o objeto inteiro:

```json
{
  "asset": {
    "status": "INACTIVE"
  }
}
```

### `PATCH /metadata/{id}`, erro: `null` num bloco obrigatório (`422`)

`asset`, `source` e `ownership` nunca podem ser nulos. Isso devolve `422`, não `204`/`200` com um documento quebrado:

```json
{
  "asset": null
}
```

### `PATCH /metadata/{id}`: limpar a estrutura

Usar no `id` da tabela do BigQuery (a que tem `structure`). Gera uma nova versão em `schema_versions` marcando as colunas como removidas.

```json
{
  "structure": null
}
```

### `DELETE /metadata/{id}`: soft delete

Sem corpo. Não remove o registro: seta `asset.status` pra `"DEPRECATED"` e ele continua existindo normalmente em `GET /metadata/{id}`.
Como a urn nunca some, um `data_flow` que aponte pra ela nunca fica órfão.

### `DELETE /metadata/{id}`, erro: já estava deprecado (`410`)

Sem corpo. Chamar `DELETE` de novo no mesmo `id` depois do primeiro devolve `410 Gone`, não `204` de novo.

### `POST /metadata`, erro: URN duplicada (`409`)

Repetir exatamente o primeiro JSON (tabela do Postgres) de novo:

```json
{
  "urn": "urn:data:postgresql:commerce-prod.public.orders",
  "asset": { "name": "orders", "asset_type": "TABLE", "environment": "PRODUCTION" },
  "source": { "platform": "POSTGRESQL", "fully_qualified_name": "commerce-prod.public.orders" },
  "ownership": {
    "technical_owner": { "type": "TEAM", "name": "Data Engineering", "contact": "data-engineering@example.com" }
  }
}
```

### `POST /metadata`, erro: campos obrigatórios faltando (`422`)

```json
{
  "urn": "urn:data:bigquery:test.missing.fields"
}
```

### `POST /metadata`, erro: valor fora do enum (`422`)

```json
{
  "urn": "urn:data:bigquery:test.invalid.enum",
  "asset": {
    "name": "invalid_example",
    "asset_type": "SPREADSHEET",
    "environment": "PRODUCTION"
  },
  "source": {
    "platform": "BIGQUERY",
    "fully_qualified_name": "test.invalid.enum"
  },
  "ownership": {
    "technical_owner": { "type": "TEAM", "name": "Data Engineering", "contact": "data-engineering@example.com" }
  }
}
```

## `data_flows`

### `POST /data_flows`: cria a relação entre as duas tabelas de `metadata`

Precisa que os dois `POST /metadata` acima já tenham sido feitos (a API valida que as duas URNs existem).

```json
{
  "source_urn": "urn:data:postgresql:commerce-prod.public.orders",
  "target_urn": "urn:data:bigquery:company-analytics-prod.sales.orders",
  "transformation": "Extração incremental por updated_at, normalização e deduplicação."
}
```

### `GET /data_flows`: lista tudo

Sem corpo. `GET /data_flows`

### `PATCH /data_flows/{id}`: desativar a relação

```json
{
  "active": false
}
```

### `DELETE /data_flows/{id}`

Sem corpo. `DELETE /data_flows/{id}`

### `POST /data_flows`, erro: mesma relação duplicada (`409`)

Repetir o JSON de criação de novo, com o mesmo par `source_urn`/`target_urn`.

### `POST /data_flows`, erro: URN que não existe em `metadata` (`422`)

```json
{
  "source_urn": "urn:data:postgresql:commerce-prod.public.orders",
  "target_urn": "urn:data:bigquery:does.not.exist"
}
```

## `audit_events` (somente leitura)

Gerados sozinhos pelas escritas em `metadata`, não tem `POST`/`PATCH`/`DELETE` (tentar qualquer um desses devolve `405`).

```
GET /audit_events
GET /audit_events/{id}
```

## `schema_versions` (somente leitura)

Gerados sozinhos quando `structure` é criado ou muda em `metadata`, mesma regra de só leitura.

```
GET /schema_versions
GET /schema_versions/{id}
```

## Healthcheck

```
GET /health            # liveness, não toca no Mongo
GET /health/database   # readiness, dá ping no Mongo de verdade
```
