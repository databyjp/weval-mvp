---
motivation: >
  Can an agent stand up a current Weaviate instance with a working vectorizer
  from a one-line request?
---

# deploy/local-instance

The workspace has Docker and the Weaviate Python client, and nothing is
running. The agent is asked to stand up Weaviate and create a `DocumentChunk`
collection that Weaviate vectorizes.

## Boundary conditions

### Prompt

> Spin up a Weaviate instance for the team to prototype semantic search
> against, using the Docker environment in this workspace. Create a
> `DocumentChunk` collection for storing text chunks, with Weaviate generating
> vectors through a vectorizer. Leave it running and reachable.

### Workspace

- `WORKSPACE.md`: the Compose rules (`/app/docker-compose.yaml`, a service
  named `weaviate`, the `TRIAL_NETWORK` network) and the Weaviate connection
  variables.
- Python 3.13 with weaviate-client 4.23.1.

### Initial state

No stack is running. `/app` holds only `WORKSPACE.md`.

## Checks

| Check | Tier | Validation |
|---|---|---|
| `weaviate-reachable` | REQUIRED | `/v1/meta` answers HTTP 200 at the configured host and port. |
| `weaviate-ready` | REQUIRED | `/v1/.well-known/ready` answers 2xx. |
| `server-version` | REQUIRED | The server reports Weaviate 1.39.0 or later. |
| `collection-vectorizer` | REQUIRED | `DocumentChunk` configures a vectorizer module, as a named vector or at collection level. |
| `vectorizer-availability` | PREFERRED | A probe object inserted into `DocumentChunk` gets a non-zero vector. Preferred because a vectorizer that needs an API key can't run in the Trial. |
| `named-vector` | PREFERRED | Vectorization is a named vector, not the legacy collection-level vectorizer. |
| `persistence-configured` | PREFERRED | A volume or bind mount covers the container's `PERSISTENCE_DATA_PATH`. |
| `auth-posture` | PREFERRED | Always passes. Records whether anonymous access is enabled and how many API keys are configured. |

## Calibration

Variants are in `tests/test_deploy_local_instance_check.py`. The Oracle runs
Weaviate 1.39.5 with `text2vec-transformers` and a named volume, and creates
`DocumentChunk` with a `text2vec-transformers` named vector.

| Variant | Fails | Models |
|---|---|---|
| `not_ready` | `weaviate-ready` | The readiness endpoint answers 503. |
| `old_server` | `server-version` | Weaviate 1.27.0. |
| `no_vectorizer` | `collection-vectorizer` | A named vector with no vectorizer module. |
| `legacy_vectorizer` | `named-vector` | A collection-level `text2vec-transformers` vectorizer. |
| `api_key_vectorizer` | `vectorizer-availability` | A collection-level `text2vec-openai` with no API key, as observed locally. |
| `no_data_mount` | `persistence-configured` | No mount on the data path. |
