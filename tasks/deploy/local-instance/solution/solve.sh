#!/bin/sh
set -eu

cp /solution/docker-compose.yaml /app/

cd /app
docker compose up --detach --wait --wait-timeout 180
pip install --no-cache-dir weaviate-client==4.23.1
python /solution/create_collection.py
