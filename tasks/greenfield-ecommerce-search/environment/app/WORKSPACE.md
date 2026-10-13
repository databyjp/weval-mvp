# Ecommerce search workspace

This directory contains the FastAPI application. Python 3.13, FastAPI, Uvicorn, and the Weaviate Python client are installed.

A Docker daemon and Docker Compose are available for supporting services. The application itself runs directly in this workspace rather than in the submitted Compose stack.

Use `/app/docker-compose.yaml` for the supporting stack. Name the database service `weaviate`. Connect the services to the existing Docker network whose name is in `TRIAL_NETWORK`; the Compose project name is already configured.

The application receives these Weaviate connection settings:

- `WEAVIATE_HTTP_HOST`
- `WEAVIATE_HTTP_PORT`
- `WEAVIATE_GRPC_HOST`
- `WEAVIATE_GRPC_PORT`

The product fixture is `/fixtures/products.json`. The application entrypoint remains `main:app` and runs on port 8000.
