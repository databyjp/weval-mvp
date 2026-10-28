#!/bin/sh
set -eu

cp \
  /solution/docker-compose.yaml \
  /solution/main.py \
  /solution/search_backend.py \
  /app/

pip install --no-cache-dir weaviate-client==4.23.1

cd /app
docker compose up --detach --wait --wait-timeout 180
