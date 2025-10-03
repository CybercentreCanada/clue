ARG base_plugin_version="0.0.8"

FROM cccsaurora/clue-plugin-base:${base_plugin_version}

COPY --chown=clue:clue . ./

RUN tree ./
