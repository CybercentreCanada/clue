# Base image
FROM node:alpine

# Creating clue-ui user (and using gid and uid 1001, since gid and uid 1000 are used by the node:node user in the base node image)
RUN addgroup -g 1001 clue-ui && adduser -u 1001 -G clue-ui -s /bin/sh -D clue-ui

# Set working directory
WORKDIR /clue-ui

# Copying the webpacked project into the working directory
COPY --chown=clue-ui:clue-ui ./dist /clue-ui/dist

RUN npm install serve -g

USER root
RUN apk update && apk add --no-cache vim htop procps

# Run container rootless
USER clue-ui:clue-ui

# start app
CMD ["serve", "-s", "dist"]
