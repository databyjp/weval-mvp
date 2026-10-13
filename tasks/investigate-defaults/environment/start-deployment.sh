#!/bin/sh
set -eu

# Only the evaluator's startup path starts the inherited deployment.
docker compose --project-directory /app up --detach --wait --wait-timeout 180
touch /tmp/weval-deployment-ready

exec "$@"
