FROM python:3.12-alpine AS base

# Make sure root account is locked so 'su' commands fail all the time
RUN passwd -l root

# Add clue user
RUN addgroup -S clue && adduser -S -G clue -h /var/lib/clue clue

# Must pass the branch and commit as parameter
ARG branch
ARG commit
ARG version

ENV BRANCH=$branch
ENV COMMIT_HASH=$commit
ENV CLUE_VERSION=$version

# Create clue config directory
RUN mkdir -p /etc/clue && \
    chmod 750 /etc/clue && \
    chown clue:clue /etc/clue

# Create clue cache directory
RUN mkdir -p /var/cache/clue
RUN chmod 770 /var/cache/clue
RUN chown clue:clue /var/cache/clue

# Create clue home directory and documentation directory
RUN mkdir -p /var/lib/clue/docs
RUN chmod 750 -R /var/lib/clue
RUN chown clue:clue -R /var/lib/clue
WORKDIR /var/lib/clue

# Create clue log directory
RUN mkdir -p /var/log/clue
RUN chmod 770 /var/log/clue
RUN chown clue:clue /var/log/clue

# Install common dependancies
RUN apk update && apk add --no-cache libsasl cyrus-sasl-dev zip vim nano && rm -rf /var/cache/apk/*

# Create a temporary image to compile dependencies
FROM base AS builder
ARG version=*

# Get required apk packages
RUN apk update && apk add --no-cache build-base gcc musl-dev libffi-dev openssl-dev && rm -rf /var/cache/apk/*

# Upgrade pip
RUN pip install --no-cache-dir --no-warn-script-location --upgrade pip && rm -rf ~/.cache/pip

# Switch user to clue to get predicatable python packages creation
USER clue

# Create a snpshot file so we know what to copy
RUN touch /tmp/before-pip

# Install clue into local so it merges new and old packages
COPY dist* dist/

USER clue
RUN pip install --no-cache-dir --no-warn-script-location --user "$(ls dist/clue_api*.whl)[server]" && \
    rm -rf ~/.cache/pip

# Remove files that existed before the pip install so that our copy command below doesn't take a snapshot of
# files that already exist in the base image
RUN find /var/lib/clue/.local -type f ! -newer /tmp/before-pip -delete

# Create a new image, without compile depedencies
FROM base
ARG version=0.0.0.dev0
ARG version_tag=${version}

# Get the updated local dir from builder
COPY --chown=clue:clue --from=builder /var/lib/clue/.local /var/lib/clue/.local
COPY --chown=clue:clue ./clue/common/classification.yml /var/lib/clue/.local/lib/python3.12/site-packages/clue/common/
COPY --chown=clue:clue ./docs /var/lib/clue/docs/

# Removing any .sh files to keep only the docss
RUN find /var/lib/clue/docs -type f -name "*.sh" -delete

# Setup Environment
ENV PATH=/var/lib/clue/.local/bin:$PATH
ENV PYTHONPATH=/var/lib/clue/.local/lib/python3.12/site-packages
ENV APP_NAME=clue
ENV APP_PREFIX=hwl
ENV CLUE_VERSION=${version}
ENV CLUE_IMAGE_TAG=${version_tag}

# Switch back to clue and run the app
USER clue

CMD ["gunicorn", "clue.patched:app", "--config=python:clue.gunicorn_config", "--worker-class", "gevent"]
