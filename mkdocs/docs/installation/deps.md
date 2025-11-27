# Kubernetes Deployment Dependencies (using Helm)

This document will guide you through the process of installing all the dependencies for deploying and managing Clue and Clue Plugins on a Kubernetes cluster.

## Overview

Clue and Clue Plugins are deployed using Helm charts, and so you'll first need to install these commandline tools:

### Installing Kubectl

If you don't have Kubectl installed, follow the [official installation guide](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/).

Verify kubectl installation:

```bash
kubectl version
```

### Installing Helm, Helm-diff and Helmfile

If you don't have Helm installed, follow the [official installation guide](https://helm.sh/docs/intro/install).

Verify helm installation:

```bash
helm version
```

It's also recommended (but not mandatory) to use helm-diff, follow the [official installation guide](https://github.com/databus23/helm-diff?tab=readme-ov-file#install).

Verify helm-diff installation:

```bash
helm diff version
```

In order to easily deploy multiple plugins, helmfile is recommended as well, follow the [official installation guide](https://helmfile.readthedocs.io/en/latest/#installation). Helmfile requires helm-diff, so make sure you've installed that as well.

```bash
helmfile version
```
