# Clue UI User-Backed deployment UI

This document will outline existing challenges in the deployment process for clue plugins, and suggest solutions.

## Problem Statement

One of the biggest issues holding back rapid iteration on clue plugins is the approach to deploying plugins. In order for a new plugin to be deployed, A number of steps must be taken:

1. Plugin is developed by the analyst
2. Plugin code is submitted to the clue-api repo as a pull request
   a. They must add their plugin to the build process
   b. They must write a Dockerfile (largely cut and paste)
   c. They must provide the same set of files as other plugins
3. A member of the clue team reviews the code, ensures basic testing is done and code standards are met
4. The plugin is merged into clue-api's codebase
5. The clue helm chart is manually edited to add the new plugin
6. The chart is updated on the cluster (requiring a full release when deploying to production)
   a. First to staging, then to production
7. Full integration testing is completed
8. Any further updates must repeat steps 2-7

This is a fairly long, involved process, in which plugin maintainers must work directly with clue developers to push updates and improvements to their plugin. This makes it a fairly unsatisfactory long-term solution.

## New Approach

Instead of the current system which requires a high degree of manual intervention form clue developers, I suggest a suite of new features, implemented over time, to slowly improve the development experience. The main set of new features are as follows:

1. User-facing deployment/redeployment of clue plugins
2. Abstraction of wider docker build process, allowing single-file deployments of clue plugins instead of requiring full docker builds

We will now break down these features, and explain how they can be implemented.

### User-facing Plugin Deployment

**Difficulty: Moderate**

Probably the most annoying part of the current paradigm is the fact that, even after first spinning up a new plugin, every single update must go through clue developers. This is the first, and likely simplest, roadblock to fix.

Kubernetes allows deployment of services/deployments via REST endpoints. The clue API can expose functionality that allows analysts to spin up and down deployments of their applications based on a template YAML file, and check the status of such a deployment. Furthermore, the clue API can allow the updating of the docker image tags, allow analysts to update the exact tag of their deployment when new builds are approved, merged and built.

The status information can come from kubenrnetes, and the image information from docker repositories. In the interest of extensibility in the open source ecosystem, these implementation can be plugin-based, allowing easy adapation of the deployment/status information to other envrironments (i.e., pulling tags from dockerhub or status from k3s/minikube/some other non-kubernetes system)

The bulk of the development effort for this approach will come in:

- integrating with azure container repositories
- integrating with the kubernetes cluster

I have no direct experience with this, but Spellbook has integrated with kubeneretes through spellbook labs, and APIs do exist to get lists of tags from azure container repositories.

### Single-file plugins

**Difficulty: Easy**

A vast majority of clue plugins are likely going to be fairly simple scripts, connecting data already existing in the world into the enrichment system clue exposes. To this end, simplifying the deployment process is important. To that end, I suggest a fission-like approach to deploying single-file enrichments.

The way this would work is as follows. A generic clue plugin container would be built, that git clones to the clue-api repository (mirrored to PB gitlab for PB deployments). It would then intialize a flask application based on the file contents, which must expose a CluePlugin class.

For example, let's imagine the repo for these "simple" scripts is located at `github.com/cybercentrecanada/clue-plugins`, and the plugin is named `example_plugin`.

The docker container would expect an environment variable `PLUGIN_ID`, and use this to initialize the flask server. We could use a bash script or python script to clone the set of scripts, and initialize the corresponding flask application.

The repository could also parameterize a basic set of unit tests to ensure the outputs of the application match expected responses, and code quality/formatting is uniform across the plugins.

The difficulty were would likely simply be outlining the development process and building the docker image. Outside of that, this is a fairly "solved" problem - airflow already does something similar.

Note that this wouldn't provide a "friendly" UI for deployment and such. It would just allow analysts to not bother with the dockerfiles and such unless they choose to.
