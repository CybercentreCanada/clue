FROM python:3.12-alpine AS base


# Make sure root account is locked so 'su' commands fail all the time
RUN passwd -l root

# Upgrade packages and get required packages
RUN apk update && apk upgrade && apk add --no-cache libffi=3.4.8-r0


FROM base as builder

ARG clue_version="clue-api"
ARG use_prereleases=1
ARG index="https://pypi.org/simple"

ENV PIP_PRE=${use_prereleases}

RUN mkdir /install
WORKDIR /install

RUN apk add --no-cache build-base=0.5-r3 libffi-dev=3.4.8-r0

RUN pip install --index=${index} --prefix=/install $clue_version

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
