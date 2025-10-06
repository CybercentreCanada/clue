ARG base_plugin_version

FROM cccsaurora/clue-plugin-base:${base_plugin_version} as builder

USER root

RUN mkdir /install
WORKDIR /install

# Get required apk packages
# RUN apk add --no-cache build-base libffi-dev

# Add pip.conf file. This allows plugin developers to customize the pip install functionality
COPY pip.conf pip.conf
ENV PIP_CONFIG_FILE pip.conf

COPY requirements.txt /tmp/requirements.txt

RUN pip install --root-user-action=ignore --no-cache --prefix=/install -r /tmp/requirements.txt

RUN rm pip.conf

FROM cccsaurora/clue-plugin-base:${base_plugin_version} as release

COPY --chown=clue:clue --from=builder /install /usr/local

COPY --chown=clue:clue . ./

RUN tree ./
