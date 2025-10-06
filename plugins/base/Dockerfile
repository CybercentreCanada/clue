FROM python:3.12-alpine AS base


# Make sure root account is locked so 'su' commands fail all the time
RUN passwd -l root

# Upgrade packages and get required packages
RUN apk update && apk upgrade && apk add --no-cache libffi=3.4.8-r0


FROM base as builder

RUN mkdir /install
WORKDIR /install

RUN apk update && apk add --no-cache build-base gcc musl-dev libffi-dev openssl-dev && rm -rf /var/cache/apk/*

# Upgrade pip
RUN pip install --no-cache-dir --no-warn-script-location --upgrade pip && rm -rf ~/.cache/pip

# Install poetry
RUN pip install --no-cache-dir --no-warn-script-location poetry && rm -rf ~/.cache/pip
ENV PATH=/install/.local/bin:$PATH

COPY clue clue

WORKDIR /install/clue

RUN poetry install --no-interaction

FROM base as release

# create local user
ARG UID=1000
RUN adduser -D -s /bin/sh -u $UID clue

# install app
USER clue

WORKDIR /home/clue
COPY --chown=clue:clue --from=builder /install/clue /home/clue/clue
RUN cp clue/plugins/files/* .

ENV APP_MODULE=patched:app
ENV PATH=/home/clue/.local/bin:/home/clue/clue/.venv/bin:$PATH
ENV PYTHONPATH=$PYTHONPATH:/home/clue/clue/.venv/lib/python3.12/site-packages

# run app
ENV GUNICORN_CONF=/home/clue/gunicorn_config.py
ENV WORKER_CLASS=gevent
ENV HOST=0.0.0.0
ENV PORT=8000
EXPOSE $PORT
ENTRYPOINT ["gunicorn", "-c", "/home/clue/gunicorn_config.py", "-k", "gevent", "--pythonpath", "/home/clue", "patched:app"]
