FROM python:3.12-alpine AS base

# Make sure root account is locked so 'su' commands fail all the time
RUN passwd -l root

# Upgrade packages and get required packages
RUN apk update && apk upgrade && apk add --no-cache libffi=3.5.2-r0

FROM base as builder
# support mirrors
ENV PIP_DISABLE_PIP_VERSION_CHECK=yes
ARG PIP_CERT
ARG PIP_CLIENT_CERT
ARG PIP_TRUSTED_HOST
ARG PIP_INDEX_URL
ARG PIP_EXTRA_INDEX_URL

RUN mkdir /install
WORKDIR /install

# Get required apk packages
RUN apk add --no-cache build-base=0.5-r3 libffi-dev=3.5.2-r0

# Copy the pip.conf and expose its environment variable.
# This will make pip install use our cccs-stratus feed.
# COPY pip.conf pip.conf
# ENV PIP_CONFIG_FILE pip.conf

# # Install dependencies
# COPY requirements.txt /tmp/requirements.txt
# RUN pip install --prefix=/install -r /tmp/requirements.txt

# # clean up pip.conf file.
# RUN rm pip.conf

FROM base as release
# create local user
ARG UID=1000
RUN adduser -D -s /bin/sh -u $UID clue

# install app
USER clue
WORKDIR /home/clue
COPY --from=builder /install /usr/local
ENV APP_MODULE=patched:app
COPY --chown=clue:clue patched.py gunicorn_config.py ./

# run app
ENV GUNICORN_CONF=/home/clue/gunicorn_config.py
ENV WORKER_CLASS=gevent
ENV HOST=0.0.0.0
ENV PORT=8000
EXPOSE $PORT
ENTRYPOINT ["gunicorn", "-c", "/home/clue/gunicorn_config.py", "-k", "gevent", "--pythonpath", "/home/clue", "patched:app"]
