FROM python:3.12-alpine AS base


# Make sure root account is locked so 'su' commands fail all the time
RUN passwd -l root

# Upgrade packages and get required packages
RUN apk update && apk upgrade && apk add --no-cache libffi=3.5.2-r0


FROM base AS builder

RUN mkdir -p /install/files
WORKDIR /install

RUN apk add --no-cache build-base=0.5-r3 libffi-dev=3.5.2-r0 openssl-dev=3.5.4-r0

# Install poetry
RUN pip install --no-cache-dir --no-warn-script-location poetry==2.2.1
ENV PATH=/install/.local/bin:$PATH

COPY ./api /install
RUN mkdir -p /install/files
COPY ./plugins/setup/files /install/files

RUN ls -a
RUN ls -a /install/clue

RUN poetry install --no-interaction

FROM base AS release

# create local user
ARG UID=1000
RUN adduser -D -s /bin/sh -u $UID clue

# install app
USER clue

WORKDIR /home/clue
COPY --chown=clue:clue --from=builder /install/clue /home/clue/clue
COPY --chown=clue:clue --from=builder /install/files/* /home/clue
COPY --chown=clue:clue --from=builder /install/.venv /home/clue/.venv

RUN ls -l /home/clue

ENV APP_MODULE=patched:app
ENV PATH=/home/clue/.local/bin:/home/clue/.venv/bin:$PATH
ENV PYTHONPATH=$PYTHONPATH:/home/clue/.venv/lib/python3.12/site-packages

# run app
ENV GUNICORN_CONF=/home/clue/gunicorn_config.py
ENV WORKER_CLASS=gevent
ENV HOST=0.0.0.0
ENV PORT=8000
EXPOSE $PORT
ENTRYPOINT ["python", "-m", "gunicorn", "-c", "/home/clue/gunicorn_config.py", "-k", "gevent", "--pythonpath", "/home/clue", "patched:app"]
