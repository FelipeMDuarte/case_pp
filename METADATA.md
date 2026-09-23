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
Para garantir unicidade teríamos que criar um Index.

### Atualização parcial (PATCH)

`PATCH /metadata/{id}` faz merge de verdade, campo a campo, até no nível mais aninhado — mandar `{"security_and_privacy": {"sensitivity": "RESTRICTED"}}` só muda `sensitivity`, sem apagar `contains_personal_data`/`regulations` que já estavam salvos. Por baixo, isso é feito achatando o payload em notação de ponto (`security_and_privacy.sensitivity`) antes de mandar pro Mongo, porque um `$set` com um dict aninhado substituiria o subdocumento inteiro em vez de só o campo enviado.

Mandar um campo explicitamente como `null` (ex: `{"structure": null}`) limpa esse campo por completo — isso é tratado como "a estrutura mudou pra vazia" e também gera uma versão em `schema_versions`.

### Busca

`GET /metadata` (e os outros `GET` de lista) aceitam qualquer campo como query param além de `skip`/`limit`, inclusive em campo aninhado via notação de ponto. A busca é parcial e não faz distinção entre maiúsculas/minúsculas, pra alguém achar "essa tabela de postgres chamada compras" sem saber exatamente como foi cadastrada no catálogo:

```
GET /metadata?asset.name=compras&source.platform=postgresql
GET /metadata?asset.domain=sales
```

A comparação é feita em Python (`MongoConnector.matches()`), não como query do Mongo: a coleção inteira é lida e o filtro é aplicado em memória antes de paginar. Deliberadamente simples: sem `$regex`, sem escapar nada, sem risco de interpretar o valor digitado como padrão de busca. O trade-off é escala: num catálogo com muitos milhares de ativos isso lê a coleção inteira a cada busca. Pra esse tamanho de projeto, a simplicidade venceu; numa base bem maior, valeria migrar pra um índice de texto do Mongo (ou Atlas Search/Elasticsearch).

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

Resumo da última checagem de qualidade do dado: `status` (`PASSED`, `WARNING`, `FAILED`), `score` (0 a 1), `checked_at` e `issues`.
Neste case, `quality` é preenchido manualmente não existe um script automático rodando checagens, mas poderia ter sem problemas.

### `structure`

A estrutura atual do dado (só faz sentido pra `asset_type: TABLE`/`VIEW`, mas o campo é opcional pra não forçar isso em outros tipos).

```json
{ "columns": [{ "name": "order_id", "data_type": "STRING", "description": "..." }] }
```

Cada vez que `structure` muda (na criação ou num `PATCH`), a API grava automaticamente um snapshot em `schema_versions`: é assim que a evolução do schema ao longo do tempo é rastreada. Ver a seção `schema_versions` abaixo.

### `last_reviewed_at`

Data da última revisão do dado (owner, classificação, documentação).

## `data_flows`

Representa o fluxo interno de dados: de onde um dado veio e pra onde foi. Uma relação por registro.

| Campo | Significado |
|---|---|
| `source_urn` | URN do metadado de origem. |
| `target_urn` | URN do metadado de destino. |
| `transformation` | Descrição livre e opcional do que foi feito nos dados entre `source` e `target`. |
| `active` | `false` quando a relação deixou de existir |

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

Um snapshot imutável da estrutura (`structure.columns`) de um documento de `metadata`, gravado toda vez que ela muda. É o que permite responder "como essa tabela era há 3 meses?" ou "quando a coluna X foi adicionada?".

| Campo | Significado |
|---|---|
| `metadata_urn` | URN do metadado cuja estrutura mudou. |
| `columns` | Snapshot completo das colunas nesse momento (não só o diff). |
| `change_summary` | Resumo gerado automaticamente do que mudou em relação à versão anterior: colunas adicionadas, removidas ou com tipo alterado. Na primeira versão, indica só a contagem inicial de colunas. |
| `detected_at` | Quando essa versão foi gravada. |

Assim como `audit_events`, não tem `PATCH`/`DELETE`, porque cada versão é um fato histórico, não algo editável.
