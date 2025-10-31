# Deployment Guide

This document provides guidance for deploying and managing the Clue API across various Kubernetes clusters.

## Overview

Deployment configurations for all clusters are maintained in the `develop` branch of the `hogwarts-stratus-deployments`
repository. This is in contrast to other applications, which match their deployments to a given branch (e.g. `master`
for production, `develop` for staging/dev). This is because plugins are often rapidly changing deployed versions, often
with individual plugins developed solely on the develop branch.

## Deployment

### Plugin Deployments

For plugin deployments, we use a simplified approach:

- Update the container image tag in the `develop` branch
- Changes are then deployed to the target cluster

## Pre-deployment Verification

Before deploying changes, it is recommended to verify that your local repository state matches the live cluster
configuration:

```bash
chart diff upgrade -n enrichment -C 3
```

If the diff shows unintended changes, review and revert them before proceeding with deployment.

```diff
enrichment, tree-viewer, Deployment (apps) has changed:
...
          null
        containers:
        - name: tree-viewer
-         image: "tree-viewer-plugin:develop"
+         image: "tree-viewer-plugin:0.12.2_main"
          imagePullPolicy: "Always"
          ports:
          - containerPort: 5000
```

### Interpreting Diff Results

The most important section to review in the diff output is the final portion showing actual deployment changes. In the
example above, note the image tag change from `develop` to `0.12.2_main` for the `tree-viewer` deployment. This
indicates that only the specified pod is being updated, which is the expected behavior for plugin deployments.
