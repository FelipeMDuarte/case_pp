# Modelo de metadados

Este documento descreve o formato usado para armazenar os metadados no MongoDB.


## Coleções

| Coleção | Conteúdo |
|---|---|
| `metadata` | Estado atual de cada dado catalogado: identidade, ownership, privacidade, camada, qualidade e estrutura atual. |
| `data_flows` | Relações de dependência entre dois documentos de `metadata` (`source_urn` → `target_urn`), de onde o dado vem e pra onde ele vai. |
| `audit_events` | Log append-only de alterações relevantes em um documento de `metadata`. |
| `schema_versions` | Log append-only da evolução da estrutura (colunas) de um documento de `metadata` ao longo do tempo. |

## `metadata`

`metadata.urn` é o identificador global do dado, é usado como FK no Mongo.
A URN não muda por causa de alterações de descrição, ownership ou classificação.
A unicidade é garantida por um índice único, tentar criar dois metadados com a mesma URN devolve `409 Conflict`.
Mesma coisa pra `data_flows`, no par (`source_urn`, `target_urn`)

Os campos com valor fechado (`asset_type`, `environment`, `status`, `layer`, `sensitivity`, `quality.status`, `ownership.*.type`, `audit_events.event_type`) são `Enum` .

### Delete é soft delete

`DELETE /metadata/{id}` não remove o documento: seta como deprecated, para manter rastreabilidade.

### Atualização parcial (PATCH)

Bloco obrigatório (não-nulo) não aceita `null` explícito. Só os campos que já são opcionais aceitam `null` como forma de limpar.
Mandar `null` nesses limpa o campo por completo.

### Busca

`GET /metadata` (e os outros `GET` de lista) aceitam qualquer campo como query param além de `skip`/`limit`. A comparação é exata e case-sensitive. O filtro vira a query do Mongo diretamente, então uma chave contendo `$` (`$where`, `$or`, etc.) é rejeitada com `422` antes de chegar no banco, para não expor operadores do Mongo pela URL.
`skip` não pode ser negativo e `limit` vai de 1 até 100.
```
GET /metadata?asset.name=compras&source.platform=POSTGRESQL
GET /metadata?asset.domain=SALES
```

### Paginação

Todo `GET` de lista devolve um envelope, não um array solto, pra quem está paginando saber quantas páginas existem.

```json
{ "items": [...], "total": 42, "skip": 0, "limit": 100 }
```

### `asset`

Identidade funcional do dado descrito por este metadado.

| Campo | Significado |
|---|---|
| `name` | Nome técnico. |
| `display_name` | Nome compreensível para usuários de negócio. |
| `description` | Explicação funcional do conteúdo. |
| `asset_type` | `TABLE`, `VIEW`, `TOPIC`, `FILE`, `DASHBOARD`, `MODEL`. |
| `environment` | `DEVELOPMENT`, `STAGING` ou `PRODUCTION`. |
| `status` | Situação operacional: `ACTIVE`, `INACTIVE`, `DEPRECATED`. |
| `domain` | Área de negócio responsável pelo dado. |
| `layer` | Camada de maturidade: `BRONZE`, `SILVER` ou `GOLD` |
| `tags` | Termos livres usados em busca e organização. |

### `source`

Localização física do dado: `platform` (ex. `BIGQUERY`, `POSTGRESQL`) e `fully_qualified_name` (nome reconhecido pela origem).

### `business_metadata`

- `purpose`: por que o dado existe.
- `grain`: o que cada linha representa.

### `ownership`

- `business_owner`: responde pelo significado e utilização do dado.
- `technical_owner`: mantém pipeline, infraestrutura e disponibilidade.
- `data_steward`: mantém definição, classificação e qualidade.

Cada owner é `{ "type": "PERSON" | "TEAM", "name": "...", "contact": "..." }`.

### `security_and_privacy`

- `sensitivity`: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL` ou `RESTRICTED`.
- `contains_personal_data`: se o dado tem dado pessoal.
- `regulations`: regulamentações aplicáveis, ex. `["LGPD"]`.

### `quality`

Neste case, `quality` é preenchido manualmente, entre 0 e 1, não existe um script automático rodando checagens, mas poderia ter sem problemas.

### `structure`

A estrutura atual do dado (só faz sentido pra `asset_type: TABLE`/`VIEW`, mas o campo é opcional pra não forçar isso em outros tipos).

```json
{ "columns": [{ "name": "order_id", "data_type": "STRING", "description": "..." }] }
```

Cada vez que `structure` muda, a API grava um snapshot em `schema_versions`, é assim que a evolução do schema ao longo do tempo é rastreada.

### `last_reviewed_at`

Data da última revisão do dado (owner, classificação, documentação).

## `data_flows`

Representa o fluxo interno de dados, de onde um dado veio e pra onde foi. Uma relação por registro.

| Campo | Significado |
|---|---|
| `source_urn` | URN do metadado de origem. |
| `target_urn` | URN do metadado de destino. |
| `transformation` | Descrição livre e opcional do que foi feito nos dados entre `source` e `target`. |
| `active` | `false` quando a relação deixou de existir |

`source_urn` e `target_urn` precisam corresponder a um `metadata` já cadastrado (`422` se não existir).

## `audit_events`

Um evento imutável por alteração relevante em um documento de `metadata`.

| Campo | Significado |
|---|---|
| `metadata_urn` | URN do metadado alterado. |
| `event_type` | `CREATED`, `UPDATED` ou `DELETED`. |
| `occurred_at` | Quando a alteração ocorreu. |
| `actor` | Quem ou o que fez a alteração. |
| `changed_fields` | Campos alterados. |

Diferente de `metadata` e `data_flows`, `audit_events` não tem `PATCH`/`DELETE` um log é append-only.

## `schema_versions`

Um snapshot imutável da estrutura de um documento de `metadata`, gravado toda vez que ela muda.

| Campo | Significado |
|---|---|
| `metadata_urn` | URN do metadado cuja estrutura mudou. |
| `columns` | Snapshot completo das colunas nesse momento. |
| `change_summary` | Resumo do que mudou em relação à versão anterior: colunas adicionadas, removidas ou com tipo alterado. Na primeira versão, indica só a contagem inicial de colunas. |
| `detected_at` | Quando essa versão foi gravada. |

Assim como `audit_events`, não tem `PATCH`/`DELETE`, porque cada versão é um fato histórico, não algo editável.
