# Stage 1: Build
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency spec first for layer caching
COPY pyproject.toml ./
RUN uv pip install --system --no-cache .

# Copy source
COPY argus/ argus/
COPY argus.yaml ./

# Stage 2: Runtime
FROM python:3.12-slim

RUN useradd --create-home --shell /bin/bash argus
USER argus
WORKDIR /home/argus

# Copy installed packages and source from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/argus /usr/local/bin/argus
COPY --from=builder /app/argus /home/argus/argus
COPY --from=builder /app/argus.yaml /home/argus/argus.yaml

ENV ARGUS_SOCKET_DIR=/tmp
ENV NO_COLOR=1

ENTRYPOINT ["argus"]
CMD ["demo"]
