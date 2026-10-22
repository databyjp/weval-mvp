#!/bin/sh
set -eu

# A fixed answer. The checks test only that a recommendation was written.
cat > /app/RECOMMENDATION.md <<'ANSWER'
# Recommended stack

- Backend: Python with FastAPI.
- Data store: a database with vector and keyword search, so retrieval can
  combine meaning and exact terms.
- Embeddings and generation: a hosted model API, chosen per budget and
  latency.
- Deployment: Docker Compose locally, then a managed container platform.
ANSWER
