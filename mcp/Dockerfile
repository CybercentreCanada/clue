# syntax=docker/dockerfile:1.7

# Fully open fallback from standard Docker Hub
FROM cgr.dev/ssc-spc.gc.ca/python:3.12-dev AS base

USER root

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

RUN apk update && \
    apk add --no-cache tzdata && \
    rm -rf /var/cache/apk/*

USER nonroot

# ==========================================
# Builder Stage
# ==========================================
FROM base AS builder

USER root

RUN apk update && apk add --no-cache build-base gcc libffi-dev openssl-dev && rm -rf /var/cache/apk/*

ARG PIP_CERT=
ENV PIP_CERT=${PIP_CERT} \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m pip install --no-cache-dir poetry

USER nonroot

ENV HOME=/var/lib/clue \
    XDG_CACHE_HOME=/var/cache/clue \
    POETRY_VIRTUALENVS_IN_PROJECT=true

# Install only locked production dependencies before copying application code.
COPY --chown=nonroot:nonroot pyproject.toml poetry.lock ./

RUN --mount=type=cache,target=/var/cache/clue/pypoetry,uid=65532,gid=65532 \
    poetry install --only main --no-root --no-interaction --no-ansi

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