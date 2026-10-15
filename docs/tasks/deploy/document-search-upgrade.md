---
motivation: >
  Can an agent upgrade a running Weaviate deployment and its Python client
  without losing data, collection configuration, or search behavior?
---

# deploy/document-search-upgrade

The stack starts on Weaviate 1.30.16 with weaviate-client 4.12.1. The prompt
names no target version. The checks require Weaviate 1.39.0 or later and
weaviate-client 4.23.0 or later, declared in `requirements.txt`. The
collection uses a legacy collection-level vectorizer, and the prompt asks the
agent to keep the collection configuration, so the upgrade must not migrate
it to a named vector.

## Boundary conditions

### Prompt

> Our document-search service needs an upgrade. Update the existing Weaviate
> deployment. Keep the indexed documents, collection configuration, and
> `/search` behavior intact. Leave the service ready for the team to use.

### Workspace

- `WORKSPACE.md`: the deployment, the 500-chunk `DocumentChunk` collection,
  the client's 4.12 release line, and the `/search` contract (query, limit 1
  to 25, default 5, and the item fields).
- `docker-compose.yaml`: Weaviate 1.30.16 and `text2vec-transformers`
  (all-MiniLM-L6-v2) with a persistent volume.
- `main.py`: a FastAPI app whose `/search` runs a near-text query on
  `DocumentChunk`.
- `requirements.txt`: pins `weaviate-client==4.12.1`.

### Initial state

`environment/start-existing-stack.sh`
- Starts the stack and seeds `DocumentChunk` with 500 chunks. The collection
  uses a collection-level `text2vec-transformers` vectorizer, and
  `document_id` uses field tokenization and is skipped by the vectorizer.
- Records the seeded objects and schema as the baseline in
  `/logs/verifier/baseline.json`, outside `/app`.
- Starts the app and confirms that `/search` answers before the agent starts.

## Checks

| Check | Tier | Validation |
|---|---|---|
| `server-version` | REQUIRED | The server reports Weaviate 1.39.0 or later. |
| `client-version` | REQUIRED | The app runs weaviate-client 4.23.0 or later, and `requirements.txt` declares a line that includes it. |
| `document-preservation` | REQUIRED | All 500 baseline chunks remain exactly once, with their UUIDs and property values. |
| `collection-schema` | REQUIRED | The schema matches the baseline: property types and tokenization, the collection-level vectorizer, and its module settings. |
| `search-contract` | REQUIRED | `/search` for "bread dough yeast fermentation" and "coral reefs ocean fish" returns 1 to 5 items with the documented fields, including a chunk with the expected title. |
| `vectorizer-availability` | REQUIRED | A new chunk gets a non-zero 384-dimension vector from the local `text2vec-transformers`. |

## Calibration

Variants are in `tests/test_deploy_document_search_upgrade_check.py`. The
Oracle advances Weaviate one minor line per restart from 1.31.22 to 1.39.7 on
the same volume, pins `weaviate-client==4.23.1`, and restarts the app.

| Variant | Fails | Models |
|---|---|---|
| `server_not_upgraded` | `server-version` | Weaviate left on 1.30.16. |
| `requirements_not_updated` | `client-version` | The client upgraded, but `requirements.txt` still pins 4.12.1. |
| `reimported_with_new_uuids` | `document-preservation` | The chunks re-imported under new UUIDs. |
| `recreated_with_default_tokenization` | `collection-schema` | The collection re-created with `document_id` on word tokenization. |
| `search_returns_server_error` | `search-contract` | `/search` answers 500. |
| `inference_service_removed` | `vectorizer-availability` | The inference service is gone, so inserts fail. |
