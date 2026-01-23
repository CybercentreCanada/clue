# Guide de déploiement Kubernetes (utilisant Helm)

Ce document fournit des conseils pour le déploiement et la gestion de Clue sur un cluster Kubernetes.

## Aperçu

Dans ce référentiel, un chart Helm est fourni qui vous permettra de déployer Clue sur un cluster Kubernetes.

## Exigences

Pour déployer Clue sur un cluster Kubernetes, vous devrez installer [kubectl](https://kubernetes.io/docs/reference/kubectl/)
ainsi que [helm](https://helm.sh/) pour installer le chart Helm fourni.

### Installation de Kubectl

Si vous n'avez pas Kubectl installé, suivez le
[guide d'installation officiel](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/).

Vérifier l'installation de kubectl :

```bash
kubectl version
```

### Installation de Helm et Helm-diff

Si vous n'avez pas Helm installé, suivez le [guide d'installation officiel](https://helm.sh/docs/intro/install).

Vérifier l'installation de helm :

```bash
helm version
```

Il est également recommandé (mais pas obligatoire) d'utiliser helm-diff, suivez le
[guide d'installation officiel](https://github.com/databus23/helm-diff?tab=readme-ov-file#install)


Vérifier l'installation de helm-diff :

```bash
helm diff version
```

## Déploiement

Voici les étapes pour déployer Clue sur votre propre cluster :

### 1. Création de l'espace de noms clue

Vous voudrez probablement installer Clue dans son propre espace de noms, et donc avant d'installer le chart, vous
devrez créer l'espace de noms en utilisant kubectl. Ici, nous créons un espace de noms appelé `clue`

```bash
kubectl create namespace clue
```

### 2. Création des secrets requis

Vous devrez générer et stocker des secrets dans le cluster :
 - flask-secret-key
 - clue-apikeys

Premièrement, le secret `flask-secret-key` est un mot de passe généré aléatoirement, voici une commande pour générer
un mot de passe de 32 caractères :
```bash
tr -dc 'A-Za-z0-9!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~' < /dev/urandom | head -c 32
```
Quant au `clue-apikeys`, il attend un objet json contenant les clés API qui permettront aux plugins de se connecter à
l'API principale. Voici à quoi cela ressemblerait :
```json
{
  "my_plugin": "some_api_key"
}
```
Si vous n'avez pas besoin de clés API, vous pouvez simplement insérer un objet json vide `{}`.

Voici la commande pour créer ces secrets en utilisant kubectl :
```bash
kubectl create secret generic flask-secret-key -n clue --from-literal=key=<generated-password>
kubectl create secret generic clue-apikeys -n clue --from-literal=data={}
```

### 3. Création de votre fichier de valeurs spécifique au déploiement

Afin d'avoir des valeurs spécifiques au déploiement, vous devrez créer un nouveau fichier
values-\<deployment>.yaml. Ce fichier n'a pas nécessairement besoin de se trouver dans ce dépôt, mais il doit être
accessible à helm.

Dans ce fichier, vous pourrez remplacer les valeurs du fichier values.yaml en conservant la même structure. Par
exemple, si vous souhaitez utiliser une balise d'image différente pour les déploiements UI et API :
```yaml
images:
  ui:
    tag: <your-tag-here>
  rest:
    tag: <your-tag-here>
```

### 4. Installation du chart helm

Voici une commande qui installera le chart Helm, en utilisant `clue` comme nom de déploiement, et en déployant dans
l'espace de noms `clue` :

```bash
# helm install <deployment-name> -n <namespace> <path-to-chart-directory> --values <path-to-deployment-specific-values>
helm install clue -n clue helm/ --values helm/values/values.yaml --values helm/values/values-deployment.yaml
```

### 5. Mise à jour du déploiement

Une fois le chart installé, si vous devez modifier quoi que ce soit dans le déploiement, vous pouvez exécuter la même
commande, en remplaçant l'option `install` par `upgrade`.

```bash
helm upgrade clue -n clue helm/ --values helm/values/values.yaml --values helm/values/values-deployment.yaml
```

## Vérification avant le déploiement

Avant de déployer des modifications, il est recommandé de vérifier que l'état de votre dépôt local correspond à la
configuration du cluster en direct en utilisant `helm diff` :

```bash
# l'option -C 3 limite la sortie à 3 lignes de chaque côté de chaque diff. Supprimez l'option pour voir le fichier entier
helm diff upgrade clue -C 3 -n clue helm/ --values helm/values/values.yaml --values helm/values/values-deployment.yaml
```

Si le diff montre des modifications non intentionnelles, examinez-les et annulez-les avant de procéder au déploiement.

## Sortie de diff attendue

### Modifications normales des certificats TLS

Lors de l'exécution de diffs, vous pouvez remarquer des modifications apportées aux certificats TLS pour le serveur
APM Elasticsearch. Ces modifications sont attendues et peuvent être ignorées en toute sécurité car elles n'affectent
pas les fonctionnalités de l'API.

L'exemple suivant illustre une sortie de diff typique :

```bash
helm diff upgrade clue -C 3 -n clue helm/ --values helm/values/values.yaml --values helm/values/values-deployment.yaml
```

Exemple de sortie :

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

### Interprétation des résultats du diff

La section la plus importante à examiner dans la sortie du diff est la partie finale montrant les modifications réelles
du déploiement. Dans l'exemple ci-dessus, notez le changement de balise d'image de `develop` à `0.12.2_main` pour le
déploiement `tree-viewer`. Cela indique que seul le pod spécifié est mis à jour, ce qui est le comportement attendu
pour les déploiements de plugins.

Toutes les autres modifications affichées dans le diff (en particulier les rotations de certificats TLS pour les
composants Elasticsearch) sont des mises à jour d'infrastructure de routine et ne nécessitent pas d'intervention.
