---
motivation: >
  Can an agent diagnose and fix a tokenization fault on a running stack
  without losing the indexed data?
---

# resolve/sku-search

Word tokenization on a SKU property splits `ZXQ-9917` into `zxq` and `9917`,
so BM25 may rank other products that share those tokens ahead of the exact match. The agent is asked to fix this.

## Boundary Conditions

### Prompt

> Customers report that searching for an exact SKU like `ZXQ-9917` shows other
> products ahead of it. The search stack and app are running in this
> workspace. Fix search without losing the indexed catalog.

### Workspace

- `WORKSPACE.md`: the `/search` contract (query, limit 1 to 25, default 5,
  and the item fields) and the Weaviate connection variables.
- `main.py`: a FastAPI app whose `/search` runs a BM25 query on `Product`.
- `docker-compose.yaml`: Weaviate 1.39.5 with a persistent volume and no
  vectorizer.

### Intial State

`environment/start-existing-stack.sh`
- Starts the stack and seeds `Product` with `sku` on word tokenization.
- Starts the app and confirms that a query for `ZXQ-9917` ranks another product first.
  - The catalog includes four SKUs that collide with `ZXQ-9917`. `9917-ZXQ` and
  `9917@ZXQ` produce the same tokens under word tokenization. `AQ1-9917` and
  `ZXQ-4831` share one token each.

## Checks

| Check | Tier | Validation |
|---|---|---|
| `exact-sku-retrieval` | REQUIRED | The reported fault is fixed: `/search` for each of the five colliding SKUs ranks that SKU first. |
| `search-contract` | REQUIRED | Non-SKU search still works: `/search` for "waterproof hiking boots" returns `TRAIL-001` with the documented fields. |
| `document-preservation` | REQUIRED | The catalog survived the fix: `Product` holds each originally seeded product exactly once, with its property values. UUIDs may change. |
| `collection-definition` | REQUIRED | The schema survived the fix: property names and data types are unchanged. `Product` may be an alias. |
| `sku-field-tokenization` | REQUIRED | The fix is in Weaviate, not the app: `sku` uses field tokenization. |
| `other-properties-word-tokenization` | PREFERRED | The fix changed only `sku`: every other seeded text property keeps word tokenization. |

## Calibration

Variants are in `tests/test_resolve_sku_search_check.py`. The Oracle copies
every object, UUIDs included, into `ProductV2` with `sku` on field
tokenization, and replaces `Product` with an alias to it.

| Variant | Fails | Models |
|---|---|---|
| `word_tokenized_ranking` | `exact-sku-retrieval` | The seeded baseline's ranking, unchanged. |
| `hoisted_filter_matches` | `exact-sku-retrieval` | Trial `HrrRY7G`'s workaround: word-tokenized filter matches, in seed order, ahead of BM25 results. |
| `exact_match_only_search` | `search-contract` | A descriptive query returns nothing. |
| `dropped_catalog` | `document-preservation` | The collection is empty. |
| `price_as_text` | `collection-definition` | `price` re-created as text. |
| `name_field_tokenization` | `other-properties-word-tokenization` | Field tokenization applied to `name` as well as `sku`. |
| `app_side_workaround` | `sku-field-tokenization` | Correct ranking with `sku` still on word tokenization. |
