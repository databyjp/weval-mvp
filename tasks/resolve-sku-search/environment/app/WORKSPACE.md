# Product search workspace

The deployment is defined in `docker-compose.yaml`. Its Weaviate service has a
persistent volume and a `Product` collection holding the indexed catalog of 28
products. The application runs from `main.py` on port 8000;
`requirements.txt` records its Python dependencies.

`GET /search?query=...&limit=...` accepts a nonempty query and a limit from 1
to 25 (default 5). It returns `{"items": [...]}` with `sku`, `name`,
`description`, `category`, and numeric `price` in each item. `/health` reports
application process readiness.

The application receives these Weaviate connection settings:

- `WEAVIATE_HTTP_HOST`
- `WEAVIATE_HTTP_PORT`
- `WEAVIATE_GRPC_HOST`
- `WEAVIATE_GRPC_PORT`
