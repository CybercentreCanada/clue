# Plugin Kubernetes Deployment Guide (using Helm and Helmfile)

This document provides guidance for deploying and managing Clue Plugins on a Kubernetes cluster.

## Overview

This repository provides helm charts that can help you deploy plugins in a Kubernetes cluster. None of this is mandatory, since in theory plugins can live anywhere, but it will give you a good starting point.

## Requirements

In order to deploy Clue to a Kubernetes cluster, you'll need to install [kubectl](https://kubernetes.io/docs/reference/kubectl/) as well as [helm](https://helm.sh/), [helm-diff](https://github.com/databus23/helm-diff/), and [helmfile](https://helmfile.readthedocs.io/) to install the provided helm charts.

You can find more information on the [Deployment Dependencies](https://cybercentrecanada.github.io/clue/installation/deps/) page.

## Creating the helm files for your plugin

### Created using the script

If you used the setup script to create your plugin, it will have prompted you to create the helm files along with it. If you selected that option, your plugin should already have a `helm/` directory, containing a `Chart.yaml` file as well as a `values/values.\<plugin-name>.yaml` file, if not, you'll need to create these.

### The main Chart file

The `Chart.yaml` uses the clue-plugin helm chart (that you can find under `plugins/base/helm/`) as a subchart, this is where all the magic happens. If your plugin is in a different location than `plugins/`, you'll need to change the `repository` value.

```yaml
dependencies:
  - name: clue-plugin
    repository: "file://../../base/helm"
    version: 0.1.x
```

### The values files

The `values.\<plugin-name>.yaml` file contains a basic configuration for your plugin, this is where you'll be managing the values of your plugin.

Since we're using the `clue-plugin` subchart, all the relevant values will go under the `clue-plugin:` root node in the yaml.

By default, only a list of plugins with only your plugin in it are included, but it's possible to change any additional settings, such as the url of the API server:

```yaml
clue-plugin:
  rest:
    full_url: http://clue-rest.clue.svc.cluster.local:5000
  plugins:
    <...>
```

If you have multiple deployments, you can also create additional values files specific to each deployment:
