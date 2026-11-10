ARG base_plugin_version

FROM alpine:3.22 AS asn_data

# Fetch the dataset at image-build time instead of keeping a repository copy.
# CI builds with --no-cache so each build downloads a fresh snapshot.
ADD https://ftp.ripe.net/ripe/asnames/asn.txt /asn.txt

FROM cccs/clue-plugin-base:${base_plugin_version} AS release

WORKDIR /home/clue
USER clue

COPY --chown=clue:clue app.py ./app.py
COPY --chown=clue:clue --from=asn_data /asn.txt ./asn.txt
