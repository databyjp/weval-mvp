# Document-search workspace

The deployment is defined in `docker-compose.yaml`. Its Weaviate service has a
persistent volume and an existing `DocumentChunk` collection with 500 indexed
document chunks. The application runs from `main.py`; `requirements.txt`
records its Python dependencies. The installed Python client starts in the
4.12 release line.

`GET /search?query=...&limit=...` accepts a nonempty query and a limit from 1
to 25 (default 5). It returns `{"items": [...]}` with `document_id`,
`chunk_index`, `title`, and `text` in each item. `/health` reports application
process readiness.
