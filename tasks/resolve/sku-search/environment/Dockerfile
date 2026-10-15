FROM docker:29.3.0-cli@sha256:067c301efe497cd5d174d468b7b3422a485ae4aca8f7ec1ffd4655c9fa383af2 AS docker-cli

FROM python:3.13-slim@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285

COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker-cli /usr/local/libexec/docker/cli-plugins/docker-compose /usr/local/libexec/docker/cli-plugins/docker-compose

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl git \
    && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir uv==0.9.25 -r /tmp/requirements.txt
COPY app/ /app/
# Evaluator seed data stays outside /app: the catalog lives only in Weaviate.
COPY weval/ /opt/weval/
COPY start-existing-stack.sh /usr/local/bin/start-existing-stack
RUN chmod +x /usr/local/bin/start-existing-stack

WORKDIR /app
ENTRYPOINT ["/usr/local/bin/start-existing-stack"]
