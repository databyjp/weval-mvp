# Weaviate workspace

A Docker daemon and Docker Compose are available. Python 3.13 and the Weaviate
Python client are installed.

Define the stack in `/app/docker-compose.yaml`. Name the database service
`weaviate`. Connect the services to the existing Docker network whose name is
in `TRIAL_NETWORK`; the Compose project name is already configured.

The team's clients connect with these settings:

- `WEAVIATE_HTTP_HOST`
- `WEAVIATE_HTTP_PORT`
- `WEAVIATE_GRPC_HOST`
- `WEAVIATE_GRPC_PORT`
