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

## Expected Diff Output

### Normal TLS Certificate Changes

When running diffs, you may notice changes to TLS certificates for the Elasticsearch APM server. These changes are
expected and can be safely ignored as they do not affect API functionality.

The following example demonstrates a typical diff output:

```bash
chart diff upgrade -n enrichment -C 3
```

Sample output:

```diff
enrichment, enrichment-elasticsearch-coordinating, StatefulSet (apps) has changed:
...
          ## Istio Labels: https://istio.io/docs/ops/deployment/requirements/
          app: coordinating-only
        annotations:
-         checksum/tls: 3cec91754cb7d9e1b8942941ba7885f20a604e0fef9c0200e569aaa46aca4b76
+         checksum/tls: b3943b1a6b7e399be8961b11b17fc849b4ebb439e0b4f9bcadb71da90584e356
      spec:
        serviceAccountName: enrichment-elasticsearch-coordinating

...
enrichment, enrichment-elasticsearch-coordinating-crt, Secret (v1) has changed:
...
    name: enrichment-elasticsearch-coordinating-crt
    namespace: enrichment
  data:
-   ca.crt: '-------- # (1147 bytes)'
-   tls.crt: '-------- # (1590 bytes)'
-   tls.key: '-------- # (1679 bytes)'
+   ca.crt: '++++++++ # (1147 bytes)'
+   tls.crt: '++++++++ # (1590 bytes)'
+   tls.key: '++++++++ # (1679 bytes)'
  type: kubernetes.io/tls

enrichment, enrichment-elasticsearch-data, StatefulSet (apps) has changed:
...
          ## Istio Labels: https://istio.io/docs/ops/deployment/requirements/
          app: data
        annotations:
-         checksum/tls: 3cec91754cb7d9e1b8942941ba7885f20a604e0fef9c0200e569aaa46aca4b76
+         checksum/tls: c27f6015bf1a57310ca320b54c9f704236d12225f76bee2ff6c0074c58acf277
      spec:
        serviceAccountName: enrichment-elasticsearch-data

...
enrichment, enrichment-elasticsearch-data-crt, Secret (v1) has changed:
...
    name: enrichment-elasticsearch-data-crt
    namespace: enrichment
  data:
-   ca.crt: '-------- # (1147 bytes)'
-   tls.crt: '-------- # (1432 bytes)'
-   tls.key: '-------- # (1679 bytes)'
+   ca.crt: '++++++++ # (1147 bytes)'
+   tls.crt: '++++++++ # (1432 bytes)'
+   tls.key: '++++++++ # (1675 bytes)'
  type: kubernetes.io/tls

enrichment, enrichment-elasticsearch-ingest, StatefulSet (apps) has changed:
...
          ## Istio Labels: https://istio.io/docs/ops/deployment/requirements/
          app: ingest
        annotations:
-         checksum/tls: 3cec91754cb7d9e1b8942941ba7885f20a604e0fef9c0200e569aaa46aca4b76
+         checksum/tls: 82df1f98f3aa097dcf3e0c69bf7a3265b6c585180716596b12967300a389ef71
      spec:
        serviceAccountName: enrichment-elasticsearch-ingest

...
enrichment, enrichment-elasticsearch-ingest-crt, Secret (v1) has changed:
...
    name: enrichment-elasticsearch-ingest-crt
    namespace: enrichment
  data:
-   ca.crt: '-------- # (1147 bytes)'
-   tls.crt: '-------- # (1444 bytes)'
-   tls.key: '-------- # (1679 bytes)'
+   ca.crt: '++++++++ # (1147 bytes)'
+   tls.crt: '++++++++ # (1444 bytes)'
+   tls.key: '++++++++ # (1679 bytes)'
  type: kubernetes.io/tls

enrichment, enrichment-elasticsearch-master, StatefulSet (apps) has changed:
...
          ## Istio Labels: https://istio.io/docs/ops/deployment/requirements/
          app: master
        annotations:
-         checksum/tls: 3cec91754cb7d9e1b8942941ba7885f20a604e0fef9c0200e569aaa46aca4b76
+         checksum/tls: efbcb4453b92715929edd33d2ba61882ef7bfde053056c0f3d794c51a01b8364
      spec:
        serviceAccountName: enrichment-elasticsearch-master

...
enrichment, enrichment-elasticsearch-master-crt, Secret (v1) has changed:
...
    name: enrichment-elasticsearch-master-crt
    namespace: enrichment
  data:
-   ca.crt: '-------- # (1147 bytes)'
-   tls.crt: '-------- # (1444 bytes)'
-   tls.key: '-------- # (1675 bytes)'
+   ca.crt: '++++++++ # (1147 bytes)'
+   tls.crt: '++++++++ # (1444 bytes)'
+   tls.key: '++++++++ # (1675 bytes)'
  type: kubernetes.io/tls

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

All other changes shown in the diff (particularly TLS certificate rotations for Elasticsearch components) are routine
infrastructure updates and do not require intervention.
