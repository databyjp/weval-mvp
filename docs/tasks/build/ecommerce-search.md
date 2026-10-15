---
motivation: >
  Can an agent build a product search API on Weaviate that supports exact SKU
  lookup, semantic queries, and pagination, configured the current way?
---

# build/ecommerce-search

The prompt asks for "a local vectorizer" without saying how to configure it.
`weaviate-managed-vectorization` requires a named vector, because
collection-level vectorizers are the legacy path in current Weaviate. The
catalog has no other SKU sharing a token with `ZXQ-9917`, so exact SKU lookup
passes under word tokenization. Field tokenization is scored separately, as
preferred.

## Boundary conditions

### Prompt

> We're prototyping search for our ecommerce catalog. Finish the starter
> FastAPI application in `/app` and back it with Weaviate. Configure the
> Product collection so Weaviate generates vectors through a local vectorizer.
> The catalog is in `/fixtures/products.json`.
>
> The frontend needs exact SKU lookup, product search, and paginated results
> through the `/search` contract documented in the starter. Use the Docker
> environment available in the workspace for supporting services, and leave
> the search stack ready for the team to try.

### Workspace

- `WORKSPACE.md`: the Compose rules (`/app/docker-compose.yaml`, a service
  named `weaviate`, the `TRIAL_NETWORK` network), the Weaviate connection
  variables, and the `main:app` entrypoint on port 8000.
- `main.py`: an empty FastAPI app whose docstring is the `/search` contract
  (`query` required, `page` default 1, `page_size` default 5, and the item
  fields).
- `/fixtures/products.json`: 24 products.
- Python 3.13 with weaviate-client 4.23.1, FastAPI, and Uvicorn.

### Initial state

No stack or application is running.

## Checks

| Check | Tier | Validation |
|---|---|---|
| `catalog-ingestion` | REQUIRED | The catalog is loaded: `Product` holds each of the 24 products exactly once. Extra properties are allowed. |
| `product-schema` | REQUIRED | `sku`, `name`, `description`, and `category` are text; `price` is a number. |
| `weaviate-managed-vectorization` | REQUIRED | Weaviate generates the vectors: `Product` has a named vector from `text2vec-ollama` or `text2vec-transformers`, and every object has a vector. |
| `search-contract` | REQUIRED | `/search` follows the starter's contract: a missing query and invalid `page` or `page_size` values get 4xx, and the default page holds 5 items with the documented fields. |
| `exact-sku-retrieval` | REQUIRED | `/search` for `ZXQ-9917` ranks it first. |
| `semantic-retrieval` | REQUIRED | `/search` for "soggy mountaineering trek" returns `TRAIL-001` on page 1. |
| `pagination` | REQUIRED | Five pages of 5 are stable, don't overlap, and match one request for 24 in order. |
| `sku-category-field-tokenization` | PREFERRED | `sku` and `category` use field tokenization. |
| `hybrid-query` | PREFERRED | The submitted code calls `.query.hybrid(...)`. |

## Calibration

Variants are in `tests/test_build_ecommerce_search_check.py`. The Oracle runs
`text2vec-transformers` beside Weaviate, creates `Product` with a named vector
and field tokenization on `sku` and `category`, and serves `/search` with
hybrid queries.

| Variant | Fails | Models |
|---|---|---|
| `legacy_vectorizer` | `weaviate-managed-vectorization` | A collection-level `text2vec-transformers` vectorizer. |
| `missing_product` | `catalog-ingestion` | `ZXQ-9917` was not ingested. |
| `word_tokenization` | `sku-category-field-tokenization` | `sku` left on word tokenization. |
| `near_text_search` | `hybrid-query` | `/search` uses `near_text` instead of hybrid. |
| `default_page_size_10` | `search-contract` | The default page size is 10. |
