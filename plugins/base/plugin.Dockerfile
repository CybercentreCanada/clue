ARG base_plugin_version

FROM cccsaurora/clue-plugin-base:${base_plugin_version} as builder

USER root

RUN mkdir /install
WORKDIR /install

# Get required apk packages
RUN apk add --no-cache build-base=0.5-r3 libffi-dev=3.4.8-r0

# Add pip.conf file. This allows plugin developers to customize the pip install functionality
COPY pip.conf pip.conf
ENV PIP_CONFIG_FILE pip.conf

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir --root-user-action=ignore --no-cache --prefix=/install -r /tmp/requirements.txt

RUN rm pip.conf

USER clue

FROM cccsaurora/clue-plugin-base:${base_plugin_version} as release

WORKDIR /home/clue

USER clue

COPY --chown=clue:clue --from=builder /install /usr/local

ENV PYTHONPATH="/usr/local/lib/python3.12/site-packages:${PYTHONPATH}"

COPY --chown=clue:clue . ./

RUN tree ./
