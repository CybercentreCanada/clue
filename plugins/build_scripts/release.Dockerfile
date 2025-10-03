ARG base_plugin_version

FROM cccsaurora/clue-plugin-base:${base_plugin_version}

COPY --chown=clue:clue . ./

RUN tree ./
