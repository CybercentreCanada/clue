# syntax=docker/dockerfile:1.7

# Fully open fallback from standard Docker Hub
FROM cgr.dev/ssc-spc.gc.ca/python:3.12-dev AS base

USER root

RUN groupadd --system --gid 65532 nonroot && \
    useradd --system --uid 65532 --gid nonroot --home-dir /var/lib/clue --create-home nonroot

# Must pass the branch and commit as parameter
ARG branch
ARG commit
ARG version

ENV BRANCH=$branch
ENV COMMIT_HASH=$commit
ENV CLUE_VERSION=$version

RUN mkdir -p /var/lib/clue && \
    mkdir -p /var/log/clue && \
    mkdir -p /var/cache/clue && \
    chmod 750 /var/lib/clue && \
    chmod 770 /var/log/clue && \
    chmod 770 /var/cache/clue && \
    chown nonroot:nonroot /var/lib/clue && \
    chown nonroot:nonroot /var/log/clue && \
    chown nonroot:nonroot /var/cache/clue && \
    chmod g+s /var/lib/clue

WORKDIR /var/lib/clue

RUN apt-get update && \
    apt-get install --yes --no-install-recommends tzdata && \
    rm -rf /var/lib/apt/lists/*

USER nonroot

# ==========================================
# Builder Stage
# ==========================================
FROM base AS builder

USER root

RUN apt-get update && \
    apt-get install --yes --no-install-recommends build-essential gcc libffi-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/*

ENV PIP_DEFAULT_TIMEOUT=120 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

ARG PIP_INDEX_URL=https://pypi.org/simple

RUN --mount=type=secret,id=pip_ca \
    PIP_CERT=/run/secrets/pip_ca \
    python -m pip install --no-cache-dir --index-url "${PIP_INDEX_URL}" poetry poetry-plugin-export

USER nonroot

ENV HOME=/var/lib/clue \
    XDG_CACHE_HOME=/var/cache/clue \
    POETRY_VIRTUALENVS_IN_PROJECT=true

# Install only locked production dependencies before copying application code.
COPY --chown=nonroot:nonroot pyproject.toml poetry.lock ./

RUN --mount=type=cache,target=/var/cache/clue/pip,uid=65532,gid=65532 \
    --mount=type=secret,id=pip_ca,uid=65532,gid=65532,mode=0400 \
    poetry export --only main --without-hashes --output /tmp/requirements.txt && \
    python -m venv .venv && \
    PIP_CERT=/run/secrets/pip_ca \
    PIP_CACHE_DIR=/var/cache/clue/pip \
    PIP_INDEX_URL="${PIP_INDEX_URL}" \
    .venv/bin/python -m pip install --requirement /tmp/requirements.txt && \
    rm /tmp/requirements.txt

COPY --chown=nonroot:nonroot . .



FROM base

# Copy the constructed workspace and virtual environment over
COPY --chown=nonroot:nonroot --from=builder /var/lib/clue/ /var/lib/clue/

USER nonroot

ENV PATH=/var/lib/clue/.venv/bin:$PATH \
    HOME=/var/lib/clue \
    XDG_CACHE_HOME=/var/cache/clue \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/var/lib/clue

EXPOSE 8000

ENTRYPOINT ["python", "-m", "clue_mcp.server"]