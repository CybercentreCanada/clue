# Deploying And Managing Clue.

This document provides guidance for deploying and managing Clue on a Kubernetes cluster.

## Overview

In this repository, a helm chart is provided that will allow you to deploy Clue to a Kubernetes cluster.

## Requirements

In order to deploy Clue to a Kubernetes cluster, you'll need to install [kubectl](https://kubernetes.io/docs/reference/kubectl/) as well as [helm](https://helm.sh/) to install the provided helm chart.

You can find more information on the [Deployment Dependencies](https://cybercentrecanada.github.io/clue/installation/deps/) page.

## Deployment

Here are the steps to deploying Clue to your own cluster:

### 1. Creating the clue namespace

You'll probably want to install Clue in it's own namespace, and so before installing the chart, you'll need to create the namespace using kubectl.
Here we're creating a namespace called `clue`

```bash
kubectl create namespace clue
```

### 2. Creating required secrets

You'll need to generate and store some secrets in the cluster:
 - flask-secret-key
 - clue-apikeys

First, the `flask-secret-key` secret is a randomly generated password, here's a command to generate a 32 character password:
```bash
tr -dc 'A-Za-z0-9!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~' < /dev/urandom | head -c 32
```
As for the `clue-apikeys`, it expects a json object containing the API Keys that will allow plugins to connect to the core API. Here's what that would look like:
```json
{
  "my_plugin": "some_api_key"
}
```
If you don't need any API Keys, you can simply insert an empty json object `{}`.

Here's the command to create those secrets using kubectl:
```bash
kubectl create secret generic flask-secret-key -n clue --from-literal=key=<generated-password>
kubectl create secret generic clue-apikeys -n clue --from-literal=data={}
```

### 3. Creating your deployment-specific values file

In order to have deployment specific values, you'll need to create a new values-\<deployment>.yaml file. This file doesn't necessarily need to live in this repo, but it needs to be accessible to helm. We usually include them under helm/values, you'll find a values.example.yaml file already there for reference

In this file, you'll be able to override values from the values.yaml file by keeping the same structure. For example, if you want to use a different image tag for the UI and API deployments:
```yaml
images:
  ui:
    tag: <your-tag-here>
  rest:
    tag: <your-tag-here>
```

### 4. Installing the helm chart

Here's a command that will install the helm chart, using `clue` as the deployment name, and deploying to the `clue` namespace:

```bash
cd helm
# helm install <deployment-name> <path-to-chart-directory> -n <namespace> --values <path-to-deployment-specific-values>
helm install clue . -n clue --values helm/values/values.yaml --values helm/values/values-deployment.yaml
```

### 5. Updating the deployment

Once the chart is installed, if you need to change anything in the deployment, you can run the same command, replacing the `install` option with `upgrade`.

```bash
helm upgrade clue -n clue helm/ --values helm/values/values.yaml --values helm/values/values-deployment.yaml
```

## Pre-deployment Verification

Before deploying changes, it is recommended to verify that your local repository state matches the live cluster
configuration using `helm diff`:

```bash
# the -C 3 option limits the output to 3 lines on each side of each diff. Remove the option to see the entire file
helm diff upgrade clue -C 3 -n clue helm/ --values helm/values/values.yaml --values helm/values/values-deployment.yaml
```

If the diff shows unintended changes, review and revert them before proceeding with deployment.

## Expected Diff Output

### Normal TLS Certificate Changes

When running diffs, you may notice changes to TLS certificates for the Elasticsearch APM server. These changes are
expected and can be safely ignored as they do not affect API functionality.

The following example demonstrates a typical diff output:

```bash
helm diff upgrade clue -C 3 -n clue helm/ --values helm/values/values.yaml --values helm/values/values-deployment.yaml
```

Sample output:

```diff
clue, clue-elasticsearch-coordinating, StatefulSet (apps) has changed:
...
          ## Istio Labels: https://istio.io/docs/ops/deployment/requirements/
          app: coordinating-only
        annotations:
-         checksum/tls: 3cec91754cb7d9e1b8942941ba7885f20a604e0fef9c0200e569aaa46aca4b76
+         checksum/tls: b3943b1a6b7e399be8961b11b17fc849b4ebb439e0b4f9bcadb71da90584e356
      spec:
        serviceAccountName: clue-elasticsearch-coordinating

...
clue, clue-elasticsearch-coordinating-crt, Secret (v1) has changed:
...
    name: clue-elasticsearch-coordinating-crt
    namespace: clue
  data:
-   ca.crt: '-------- # (1147 bytes)'
-   tls.crt: '-------- # (1590 bytes)'
-   tls.key: '-------- # (1679 bytes)'
+   ca.crt: '++++++++ # (1147 bytes)'
+   tls.crt: '++++++++ # (1590 bytes)'
+   tls.key: '++++++++ # (1679 bytes)'
  type: kubernetes.io/tls

clue, clue-elasticsearch-data, StatefulSet (apps) has changed:
...
          ## Istio Labels: https://istio.io/docs/ops/deployment/requirements/
          app: data
        annotations:
-         checksum/tls: 3cec91754cb7d9e1b8942941ba7885f20a604e0fef9c0200e569aaa46aca4b76
+         checksum/tls: c27f6015bf1a57310ca320b54c9f704236d12225f76bee2ff6c0074c58acf277
      spec:
        serviceAccountName: clue-elasticsearch-data

...
clue, clue-elasticsearch-data-crt, Secret (v1) has changed:
...
    name: clue-elasticsearch-data-crt
    namespace: clue
  data:
-   ca.crt: '-------- # (1147 bytes)'
-   tls.crt: '-------- # (1432 bytes)'
-   tls.key: '-------- # (1679 bytes)'
+   ca.crt: '++++++++ # (1147 bytes)'
+   tls.crt: '++++++++ # (1432 bytes)'
+   tls.key: '++++++++ # (1675 bytes)'
  type: kubernetes.io/tls

clue, clue-elasticsearch-ingest, StatefulSet (apps) has changed:
...
          ## Istio Labels: https://istio.io/docs/ops/deployment/requirements/
          app: ingest
        annotations:
-         checksum/tls: 3cec91754cb7d9e1b8942941ba7885f20a604e0fef9c0200e569aaa46aca4b76
+         checksum/tls: 82df1f98f3aa097dcf3e0c69bf7a3265b6c585180716596b12967300a389ef71
      spec:
        serviceAccountName: clue-elasticsearch-ingest

...
clue, clue-elasticsearch-ingest-crt, Secret (v1) has changed:
...
    name: clue-elasticsearch-ingest-crt
    namespace: clue
  data:
-   ca.crt: '-------- # (1147 bytes)'
-   tls.crt: '-------- # (1444 bytes)'
-   tls.key: '-------- # (1679 bytes)'
+   ca.crt: '++++++++ # (1147 bytes)'
+   tls.crt: '++++++++ # (1444 bytes)'
+   tls.key: '++++++++ # (1679 bytes)'
  type: kubernetes.io/tls

clue, clue-elasticsearch-master, StatefulSet (apps) has changed:
...
          ## Istio Labels: https://istio.io/docs/ops/deployment/requirements/
          app: master
        annotations:
-         checksum/tls: 3cec91754cb7d9e1b8942941ba7885f20a604e0fef9c0200e569aaa46aca4b76
+         checksum/tls: efbcb4453b92715929edd33d2ba61882ef7bfde053056c0f3d794c51a01b8364
      spec:
        serviceAccountName: clue-elasticsearch-master

...
clue, clue-elasticsearch-master-crt, Secret (v1) has changed:
...
    name: clue-elasticsearch-master-crt
    namespace: clue
  data:
-   ca.crt: '-------- # (1147 bytes)'
-   tls.crt: '-------- # (1444 bytes)'
-   tls.key: '-------- # (1675 bytes)'
+   ca.crt: '++++++++ # (1147 bytes)'
+   tls.crt: '++++++++ # (1444 bytes)'
+   tls.key: '++++++++ # (1675 bytes)'
  type: kubernetes.io/tls

clue, tree-viewer, Deployment (apps) has changed:
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
