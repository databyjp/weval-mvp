# Weaviate deployment workspace

The deployment is defined in `docker-compose.yaml` and is already running.
A Docker daemon and Docker Compose are available. Python 3.13 and the Weaviate
Python client are installed.

The deployment's clients connect with these settings:

- `WEAVIATE_HTTP_HOST`
- `WEAVIATE_HTTP_PORT`
- `WEAVIATE_GRPC_HOST`
- `WEAVIATE_GRPC_PORT`

## Audit format

`/app/audit.json` is one JSON object with these fields:

| Field | Type | Meaning |
|---|---|---|
| `server_version` | string | Weaviate server version, for example `"1.30.0"` |
| `vectorizer_modules` | list of strings | Names of the vectorizer modules available on the server |
| `default_vectorizer` | string or null | The vectorizer a new collection uses when none is specified; `null` if there is none |
| `anonymous_access` | boolean | Whether requests without credentials are accepted |
