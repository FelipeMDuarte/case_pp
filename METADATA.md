# Modelo de metadados

Este documento descreve o formato usado para armazenar os metadados no MongoDB.


## Coleções

| Coleção | Conteúdo |
|---|---|
| `metadata` | Estado atual de cada dado catalogado: identidade, ownership, privacidade, camada e qualidade. |
| `data_flows` | Relações de dependência entre dois documentos de `metadata` (`source_urn` → `target_urn`) — de onde o dado vem e pra onde ele vai. |
| `audit_events` | Log append-only de alterações relevantes em um documento de `metadata`. |

## `metadata`

`metadata.urn` é o identificador global do dado, é usado como FK no Mongo.
A URN não muda por causa de alterações de descrição, ownership ou classificação.
Para garantir unicidade teríamos que criar um Index.

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
