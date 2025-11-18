# Guide de développement de l'API Clue

Ce guide décrit comment configurer un environnement de développement pour l'API Clue.

## Prérequis

Avant de commencer, assurez-vous d'avoir installé les éléments suivants sur votre système :

- Python 3.10, 3.11 ou 3.12 (3.12 recommandé)
- [Poetry](https://python-poetry.org/docs/#installation) pour la gestion des dépendances
- Docker et Docker Compose pour les dépendances de test
- Git

## Configuration de l'environnement de développement

### 1. Cloner le dépôt

```bash
git clone https://github.com/CybercentreCanada/clue.git
cd clue/api
```

### 2. Installer Poetry

Si vous n'avez pas Poetry installé, suivez le [guide d'installation officiel](https://python-poetry.org/docs/#installation).

Vérifier l'installation de Poetry :

```bash
poetry --version
```

### 3. Configurer l'environnement Python

Configurer Poetry pour utiliser Python 3.12 (ou votre version préférée) :

```bash
poetry env use 3.12
```

Vérifier l'environnement :

```bash
poetry env info
```

### 4. Installer les dépendances

Installer toutes les dépendances, y compris les dépendances de développement et de test :

```bash
poetry install --all-extras --with test,dev,types
```

Cela installera :

- Les dépendances principales
- Les extras du serveur (Werkzeug, bcrypt, PyYAML, etc.)
- Les dépendances de test (pytest, mypy, coverage, etc.)
- Les dépendances de développement (pre-commit, ruff, etc.)
- Les dépendances de vérification de type

### 5. Créer les répertoires et la configuration requis

Créer les répertoires nécessaires pour la configuration et les journaux de Clue :

```bash
sudo mkdir -p /etc/clue/conf/
sudo mkdir -p /etc/clue/lookups/
sudo mkdir -p /var/log/clue
sudo chmod a+rw /etc/clue/conf/
sudo chmod a+rw /etc/clue/lookups/
sudo chmod a+rw /var/log/clue
```

Copier les fichiers de configuration :

```bash
cp build_scripts/classification.yml /etc/clue/conf/classification.yml
cp test/unit/config.yml /etc/clue/conf/config.yml
```

### 6. Démarrer les dépendances de test

Démarrer les services requis (Redis et Keycloak) à l'aide de Docker Compose :

```bash
cd dev
docker-compose up --build -d
cd ..
```

Attendre que les services soient en bonne santé :

```bash
poetry run python build_scripts/keycloak_health.py
```

## Flux de travail de développement

### Qualité et formatage du code

Le projet utilise plusieurs outils pour maintenir la qualité du code :

```bash
# Vérifier le formatage
poetry run ruff format clue --diff

# Appliquer le formatage
poetry run ruff format clue

# Exécuter les vérifications du linter
poetry run ruff check clue

# Corriger les problèmes auto-corrigibles
poetry run ruff check clue --fix

# Exécuter la vérification de type
poetry run type_check

# Exécuter tous les tests
poetry run test
```

#### Tester des fichiers ou des fonctions spécifiques

```bash
# Exécuter des fichiers de test spécifiques
poetry run pytest test/unit/test_specific_module.py

# Exécuter des fonctions de test spécifiques
poetry run pytest test/unit/test_specific_module.py::test_function_name
```

### Démarrer le serveur de développement

Démarrer le serveur API Clue :

```bash
poetry run server
```

Le serveur démarrera et sera disponible sur le port configuré, généralement 5000 (vérifiez votre config.yml et les variables d'environnement pour plus de détails).

### Tester les services d'enrichissement

Pour tester les connexions aux plugins depuis l'API centrale, vous devrez peut-être démarrer des serveurs de test supplémentaires :

```bash
# Terminal 1
poetry run flask --app test.utils.test_server run --no-reload --port 5008

# Terminal 2
poetry run flask --app test.utils.bad_server run --no-reload --port 5009

# Terminal 3
poetry run flask --app test.utils.slow_server run --no-reload --port 5010

# Terminal 4
poetry run flask --app test.utils.telemetry_server run --no-reload --port 5011
```

## Structure du projet

```text
api/
├── clue/              # Code de l'application principale
│   ├── api/           # Points de terminaison de l'API
│   ├── cache/         # Utilitaires de mise en cache
│   ├── common/        # Utilitaires et assistants communs
│   ├── constants/     # Constantes de l'application
│   ├── cronjobs/      # Tâches planifiées
│   ├── extensions/    # Extensions Flask
│   ├── helper/        # Modules d'assistance
│   ├── models/        # Modèles de données
│   ├── plugin/        # Système de plugins
│   ├── remote/        # Intégrations de services distants
│   ├── security/      # Modules de sécurité
│   └── services/      # Services de logique métier
├── build_scripts/     # Scripts de construction et utilitaires
├── dev/               # Fichiers d'environnement de développement
├── docs/              # Documentation
├── scripts/           # Scripts utilitaires
└── test/              # Fichiers de test
    ├── integration/   # Tests d'intégration
    ├── unit/          # Tests unitaires
    └── utils/         # Utilitaires de test
```

## Scripts Poetry disponibles

Le projet définit plusieurs scripts pratiques dans `pyproject.toml` :

- `poetry run server` - Démarrer le serveur API Clue
- `poetry run test` - Exécuter la suite de tests
- `poetry run type_check` - Exécuter la vérification de type
- `poetry run coverage_report` - Générer des rapports de couverture (doit être exécuté après `test`)
- `poetry run plugin` - Gestion interactive des plugins

## Configuration

### Variables d'environnement

Les variables d'environnement suivantes peuvent remplacer les paramètres de configuration :

- `CLUE_CONFIG_PATH` - Chemin vers le fichier de configuration principal (par défaut : `/etc/clue/conf/config.yml`)
- `CLUE_CLASSIFICATION_PATH` - Chemin vers le fichier de classification (par défaut : `/etc/clue/conf/classification.yml`)
- `CLUE_PLUGIN_DIRECTORY` - Chemin vers l'emplacement où sont stockées les extensions clue de l'API centrale (par défaut : `/etc/clue/plugins`)
- `CLUE_SESSION_COOKIE_SAMESITE` - Définir l'attribut SameSite pour les cookies de session. Doit être `Strict`, `Lax` ou `None` pour la sécurité
- `CLUE_HSTS_MAX_AGE` - Valeur max-age de HTTP Strict Transport Security en secondes pour une sécurité HTTPS améliorée
- `FLASK_ENV` - Environnement Flask (development/production)
- `FLASK_DEBUG` - Activer le mode de débogage Flask
- `REDIS_HOST` - Remplacer le nom d'hôte Redis
- `REDIS_PORT` - Remplacer le port Redis

### Fichiers de configuration

Clue utilise deux fichiers de configuration principaux :

- `/etc/clue/conf/config.yml` - Configuration principale de l'application
- `/etc/clue/conf/classification.yml` - Configuration de classification

#### Configuration principale (`config.yml`)

Le fichier de configuration principal définit tous les aspects du serveur API Clue. Voici les sections clés :

##### Configuration de l'API

```yaml
api:
  # Paramètres de sécurité
  secret_key: "votre-clé-secrète-ici"  # Clé secrète Flask pour les sessions
  session_duration: 3600              # Durée de session en secondes (1 heure)
  validate_session_ip: true           # Valider que l'IP de session correspond
  validate_session_useragent: true    # Valider que le user agent de session correspond
  validate_session_xsrf_token: true   # Activer la validation du jeton XSRF

  # Débogage et audit
  debug: false                        # Activer le mode de débogage Flask
  audit: true                         # Journaliser les appels API pour l'audit

  # Découverte de services
  discover_url: null                  # URL optionnelle de découverte de services

  # Sources d'enrichissement externes
  external_sources: []                # Liste des services d'enrichissement externes

  # Cibles OAuth On Behalf Of (OBO)
  obo_targets: {}                     # Services auxquels Clue peut effectuer OBO
```

##### Configuration d'authentification

```yaml
auth:
  # Authentification par clé API
  allow_apikeys: false               # Activer l'authentification par clé API
  apikeys:                          # Correspondance des clés API aux identifiants utilisateur
    "api-key-1": "user1"
    "api-key-2": "user2"

  # Paramètres OAuth
  oauth:
    enabled: false                   # Activer l'authentification OAuth
    gravatar_enabled: false          # Activer Gravatar pour les avatars utilisateur
    other_audiences: []              # Audiences JWT supplémentaires à accepter
    providers: {}                    # Configurations des fournisseurs OAuth

  # Authentification de compte de service
  service_account:
    enabled: false                   # Activer l'authentification de compte de service
    accounts: []                     # Liste des informations d'identification de compte de service

  # Propagation de jeton
  propagate_clue_key: true          # Inclure le jeton Clue dans les requêtes OBO
```

##### Configuration des services principaux

```yaml
core:
  # Configuration Redis
  redis:
    host: "127.0.0.1"               # Nom d'hôte du serveur Redis
    port: 6379                      # Port du serveur Redis

  # Extensions à charger
  extensions: []                    # Liste des extensions Clue à charger

  # Collecte de métriques
  metrics:
    export_interval: 5              # Intervalle d'exportation des métriques en secondes
    redis:                          # Instance Redis pour les métriques
      host: "127.0.0.1"
      port: 6379
    apm_server:                     # Surveillance des performances d'application
      server_url: null              # URL du serveur APM
      token: null                   # Jeton d'authentification APM
```

##### Configuration de journalisation

```yaml
logging:
  # Niveaux de journalisation : DEBUG, INFO, WARNING, ERROR, CRITICAL, DISABLED
  log_level: "DEBUG"                # Niveau de journalisation actuel

  # Destinations de sortie
  log_to_console: true              # Journaliser dans la console/stdout
  log_to_file: false                # Journaliser dans des fichiers
  log_to_syslog: false              # Journaliser vers un serveur syslog

  # Paramètres de journalisation de fichier
  log_directory: "/var/log/clue/"   # Répertoire pour les fichiers journaux
  log_as_json: false                # Utiliser le format JSON pour les journaux

  # Paramètres Syslog
  syslog_host: "localhost"          # Nom d'hôte du serveur syslog
  syslog_port: 514                  # Port du serveur syslog

  # Surveillance de santé
  heartbeat_file: null              # Fichier à toucher pour les vérifications de santé
  export_interval: 5                # Intervalle de journalisation du compteur
```

##### Configuration de l'interface utilisateur

```yaml
ui:
  cors_origins: []                  # Origines CORS autorisées pour l'interface utilisateur web
```

##### Configuration de source externe

Lors de la configuration des sources d'enrichissement externes, chaque source prend en charge ces options :

```yaml
api:
  external_sources:
    - name: "exemple-source"              # Nom de source unique
      url: "https://api.exemple.com"      # URL de l'API source
      classification: "TLP:CLEAR"         # Niveau de classification minimum
      max_classification: "TLP:RED"       # Niveau de classification maximum
      include_default: true               # Inclure dans les requêtes par défaut
      production: false                   # Indicateur de prêt pour la production
      default_timeout: 30                 # Délai d'attente de requête en secondes
      built_in: true                      # Indicateur de source intégrée
      maintainer: "Admin <admin@exemple.com>"  # Contact RFC-5322
      documentation_link: "https://docs.exemple.com"  # URL de documentation
      datahub_link: "https://datahub.exemple.com"      # Entrée DataHub
      obo_target: null                    # Nom de la cible OBO
```

##### Configuration du fournisseur OAuth

Pour l'authentification OAuth, configurez les fournisseurs comme ceci :

```yaml
auth:
  oauth:
    enabled: true
    providers:
      keycloak:
        client_id: "clue-api"                    # ID client OAuth
        client_secret: "votre-secret-client"     # Secret client OAuth
        audience: "clue-api"                     # Audience JWT
        scope: "openid profile email groups"    # Portées OAuth
        jwks_uri: "https://auth.exemple.com/realms/clue/protocol/openid-connect/certs"
        access_token_url: "https://auth.exemple.com/realms/clue/protocol/openid-connect/token"
        authorize_url: "https://auth.exemple.com/realms/clue/protocol/openid-connect/auth"
        api_base_url: "https://auth.exemple.com/realms/clue/protocol/openid-connect"

        # Gestion des utilisateurs
        auto_create: true                        # Créer automatiquement les utilisateurs
        auto_sync: false                         # Synchroniser automatiquement les données utilisateur
        required_groups: ["clue-users"]          # Groupes OAuth requis

        # Correspondance de rôle et de classification
        role_map:                                # Correspondre les groupes OAuth aux rôles Clue
          "clue-admins": "admin"
          "clue-analysts": "analyst"
        classification_map:                      # Correspondre les groupes OAuth aux niveaux d'habilitation
          "clue-admins": "TLP:RED"
          "clue-analysts": "TLP:AMBER"

        # Configuration de l'ID utilisateur
        uid_randomize: false                     # Générer des noms d'utilisateur aléatoires
        uid_regex: "^(.+)@exemple\\.com$"       # Extraire le nom d'utilisateur de l'e-mail
        uid_format: "{0}"                        # Chaîne de format de nom d'utilisateur
```

#### Configuration de classification (`classification.yml`)

La configuration de classification définit le système de classification des données utilisé par Clue. Ce fichier suit le format du moteur de classification Assemblyline.

Pour des informations détaillées sur la configuration du moteur de classification, consultez la [Documentation du moteur de classification Assemblyline](https://cybercentrecanada.github.io/assemblyline4_docs/installation/classification_engine/).

Aspects clés de la configuration de classification :

- **Niveaux de classification** : Définir les niveaux de classification hiérarchiques (par exemple, TLP:CLEAR, TLP:GREEN, TLP:AMBER, TLP:RED)
- **Classifications requises** : Spécifier les niveaux de classification minimum pour différents types de données
- **Règles d'application** : Configurer comment les classifications sont appliquées et propagées
- **Schémas de marquage** : Définir les marquages visuels et textuels pour les données classifiées

Exemple de configuration de classification de base :

```yaml
classification:
  enforce: true
  dynamic_groups: false
  levels:
    - TLP:CLEAR
    - TLP:GREEN
    - TLP:AMBER
    - TLP:RED
  required:
    - TLP:CLEAR
  groups:
    - name: "TLP"
      short_name: "TLP"
      description: "Traffic Light Protocol"
      auto_select: true
```

#### Validation de la configuration

Clue valide la configuration par rapport à un schéma JSON au démarrage. Si la configuration n'est pas valide, le serveur ne démarrera pas et affichera des messages d'erreur descriptifs indiquant quels paramètres doivent être corrigés.

## Développement Docker

### Construction de l'image Docker

Construire l'image Docker de développement :

```bash
poetry build
docker build -t clue-api:dev .
```

### Docker Compose pour la pile complète

L'environnement de développement utilise Docker Compose pour fournir des services essentiels pour les tests et le développement. Le fichier `api/dev/docker-compose.yml` définit les services suivants :

#### Service Redis

```yaml
redis:
  image: redis
  ports:
    - "6379:6379"
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 30s
    timeout: 10s
    retries: 3
```

**Objectif** : Redis sert de couche de mise en cache et de stockage de session pour Clue. Il est utilisé pour :

- Gestion de session et état d'authentification utilisateur
- Mise en cache des résultats d'enrichissement pour améliorer les performances
- Limitation de débit et gestion des quotas
- Agrégation de métriques et stockage de données temporaires

**Notes de développement** :

- Exposé sur le port standard 6379
- Comprend des vérifications de santé pour s'assurer que le service est prêt avant l'exécution des tests
- Aucune persistence configurée - les données sont perdues lorsque le conteneur s'arrête (approprié pour le développement)

#### Service Keycloak (Construction personnalisée)

```yaml
keycloak:
  build:
    context: ./keycloak
    dockerfile: Dockerfile
    no_cache: true
  environment:
    KC_HEALTH_ENABLED: true
  ports:
    - "9100:8080"
  expose:
    - "9100"
  healthcheck:
    test: ["CMD-SHELL", "curl -f http://localhost:8080/health/ready"]
    interval: 5s
    timeout: 5s
    retries: 15
```

**Objectif** : Keycloak fournit des services d'authentification OAuth/OpenID Connect pour tester les flux d'authentification dans Clue.

**Fonctionnalités du Dockerfile personnalisé** :
L'image Keycloak personnalisée (`api/dev/keycloak/Dockerfile`) étend l'image officielle Keycloak 18.0.2 avec :

- **Compte administrateur préconfiguré** :
  - Nom d'utilisateur : `admin`
  - Mot de passe : `admin`
  - Permet un accès immédiat à la console d'administration Keycloak

- **Mode de développement** : Fonctionne en mode développement avec le débogage activé pour un dépannage plus facile

- **Realm préimporté** : Importe automatiquement la configuration de realm incluse depuis `keycloak-realm.json`

- **Fonctionnalités améliorées** : Active l'échange de jetons et les fonctionnalités d'autorisation à granularité fine qui peuvent être utilisées par Clue

**Utilisateurs de test préconfigurés** :
Le realm importé comprend plusieurs utilisateurs de test pour le développement et les tests :

- `admin` - Utilisateur administratif
- `dewey`, `donald`, `goose` - Utilisateurs de test standard
- `guest` - Utilisateur invité avec des autorisations limitées
- `huey`, `louie` - Utilisateurs de test supplémentaires

**Points forts de la configuration du Realm** :
Le fichier `keycloak-realm.json` configure un realm intégré avec :

- **Applications clientes** : Clients OAuth préconfigurés pour l'intégration de l'API Clue
- **Groupes d'utilisateurs** : Différents groupes d'utilisateurs avec différents niveaux d'autorisation
- **Flux d'authentification** : Flux OAuth standard pour l'authentification web et API
- **Paramètres de sécurité** : En-têtes de sécurité appropriés et gestion de session
- **Internationalisation** : Prise en charge des langues anglaise et française
- **Durées de vie des jetons** : Configuré pour le développement (durées de vie plus courtes pour les tests)

#### Démarrage de la pile de développement

Pour démarrer tous les services de développement :

```bash
cd api/dev
docker-compose up --build -d
```

Pour vérifier que les services sont en bonne santé :

```bash
# Vérifier l'état du service
docker-compose ps

# Vérifier les journaux si nécessaire
docker-compose logs redis
docker-compose logs keycloak

# Ou utiliser la vérification de santé intégrée
poetry run python build_scripts/keycloak_health.py
```

#### Accès aux services

- **Redis** : Disponible à `localhost:6379` (aucune authentification requise)
- **Console d'administration Keycloak** : `http://localhost:9100/admin`
  - Nom d'utilisateur : `admin`
  - Mot de passe : `admin`
- **Realm Keycloak** : `http://localhost:9100/realms/HogwartsMini`

#### Arrêt et nettoyage

```bash
# Arrêter les services
docker-compose down

# Arrêter et supprimer les volumes (repartir à zéro)
docker-compose down -v

# Reconstruire à partir de zéro
docker-compose down -v && docker-compose up --build
```

#### Intégration avec l'API Clue

Lorsque l'API Clue est configurée pour l'authentification OAuth, elle peut se connecter à l'instance Keycloak locale en utilisant :

```yaml
auth:
  oauth:
    enabled: true
    providers:
      keycloak:
        client_id: "clue-api"
        jwks_uri: "http://localhost:9100/realms/HogwartsMini/protocol/openid-connect/certs"
        access_token_url: "http://localhost:9100/realms/HogwartsMini/protocol/openid-connect/token"
        authorize_url: "http://localhost:9100/realms/HogwartsMini/protocol/openid-connect/auth"
        api_base_url: "http://localhost:9100/realms/HogwartsMini/protocol/openid-connect"
        # ... autre configuration
```

Cette configuration fournit un environnement de développement complet pour tester l'authentification, l'autorisation, la mise en cache et toutes les fonctionnalités de l'API Clue sans nécessiter de services externes.

## Contribution

### Hooks de pré-commit

Installer les hooks de pré-commit pour exécuter automatiquement les vérifications avant les commits :

```bash
poetry run pre-commit install
```

### Stratégie de branche

Le projet Clue suit un modèle de branchement Git flow pour assurer des versions stables et un développement organisé :

#### Branches principales

- **`main`** : Contient le code prêt pour la production. Toutes les versions sont étiquetées à partir de cette branche. Les commits directs vers `main` sont restreints.
- **`develop`** : La branche d'intégration pour les nouvelles fonctionnalités et la branche de développement principale. Toutes les branches de fonctionnalités sont créées à partir de et fusionnées dans `develop`.

#### Branches de support

- **Branches de fonctionnalités** : Créées à partir de `develop` pour de nouvelles fonctionnalités ou améliorations. Utilisez des noms descriptifs comme `feature/add-oauth-provider` ou `feature/improve-caching`.
- **Branches de version** : Créées à partir de `develop` lors de la préparation d'une nouvelle version (par exemple, `release/v2.1.0`). Utilisées pour les tests finaux et les corrections de bugs mineurs.
- **Branches de correctif** : Créées à partir de `main` pour les corrections de bugs critiques nécessitant un déploiement immédiat (par exemple, `hotfix/security-patch`).

#### Flux de travail de développement

1. **Développement de fonctionnalités** : Créer une branche de fonctionnalité à partir de `develop`
2. **Intégration** : Fusionner les fonctionnalités terminées dans `develop` via une pull request
3. **Préparation de version** : Créer une branche de version à partir de `develop` lorsque prêt pour la version
4. **Version de production** : Fusionner la branche de version dans `main` et `develop`, puis étiqueter la version
5. **Correctifs** : Si des problèmes critiques sont trouvés en production, créer des branches de correctif à partir de `main`

### Processus de pull request

Toutes les modifications de code doivent passer par le processus de pull request pour garantir la qualité du code et maintenir les normes du projet :

#### Pour les contributeurs avec accès en écriture

1. **Créer une branche de fonctionnalité** : Créer une nouvelle branche à partir de `develop` avec un nom descriptif

   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/nom-de-votre-fonctionnalité
   ```

2. **Implémenter les modifications** : Effectuer vos modifications en suivant les normes de codage du projet et en incluant les tests appropriés

3. **Vérifications avant soumission** : Avant d'ouvrir une PR, assurez-vous :
   - Tous les tests passent : `poetry run test`
   - Le code est correctement formaté : `poetry run ruff format clue`
   - Le linting passe : `poetry run ruff check clue`
   - La vérification de type passe : `poetry run type_check`

   Notez que l'installation des hooks de pré-commit aidera également à gérer ces cas.

4. **Ouvrir une pull request** : Créer une PR ciblant la branche `develop` avec :
   - Titre clair et descriptif
   - Description détaillée des modifications
   - Référence à tous les problèmes connexes
   - Captures d'écran ou exemples si applicable

#### Pour les contributeurs externes

1. **Fork du dépôt** : Fork le dépôt Clue sur votre compte GitHub

2. **Cloner et configurer** : Cloner votre fork et configurer l'environnement de développement comme décrit dans ce guide

3. **Créer une branche de fonctionnalité** : Créer une branche à partir de `develop` dans votre fork

4. **Implémenter et tester** : Effectuer vos modifications et vous assurer que toutes les vérifications passent

5. **Soumettre une pull request** : Ouvrir une PR de la branche de fonctionnalité de votre fork vers la branche `develop` du dépôt principal

#### Processus de révision

- **Approbations requises** : Toutes les pull requests nécessitent **au moins deux approbations** des mainteneurs du projet
- **Vérifications automatisées** : Les PR doivent passer toutes les vérifications automatisées, y compris :
  - Tests unitaires et tests d'intégration
  - Formatage et linting du code
  - Vérification de type
  - Analyses de sécurité

- **Révision du code** : Les réviseurs examineront :
  - La qualité du code et le respect des normes du projet
  - Couverture et qualité des tests
  - Mises à jour de la documentation si nécessaire
  - Implications de sécurité
  - Considérations de performance

#### Fusion et version

- **Fusion vers Develop** : Une fois approuvée et toutes les vérifications passées, la PR est fusionnée dans `develop`
- **Cycle de version** : Les fonctionnalités fusionnées dans `develop` seront incluses dans la prochaine version lorsque `develop` sera fusionné dans `main`
- **Calendrier de version** : Les calendriers de version sont déterminés par les mainteneurs du projet en fonction de la disponibilité des fonctionnalités et de l'achèvement des tests. Il n'y a pas de durée garantie entre la fusion et la version.

#### Meilleures pratiques

Afin de maintenir une haute qualité de code dans clue :

- Garder les PR ciblées et de taille raisonnable
- Inclure une couverture de test complète pour les nouvelles fonctionnalités
- Mettre à jour la documentation pour les modifications orientées utilisateur
- Rebaser votre branche si demandé pour maintenir un historique propre
  - Toutes les PR seront fusionnées par squash dans le tronc.

## Dépannage

### Problèmes d'environnement

Si vous rencontrez des problèmes avec l'environnement Python :

1. Supprimer l'environnement existant : `poetry env remove python`
2. Le recréer : `poetry env use 3.12`
3. Réinstaller les dépendances : `poetry install --all-extras --with test,dev,types`

### Dépendances de service

Si les services Docker ne démarrent pas correctement :

1. Arrêter tous les conteneurs : `docker-compose down`
2. Supprimer les volumes : `docker-compose down -v`
3. Reconstruire : `docker-compose up --build`

## Ressources supplémentaires

- [Documentation Poetry](https://python-poetry.org/docs/)
- [Documentation Ruff](https://docs.astral.sh/ruff/)
- [Documentation pytest](https://docs.pytest.org/)
- [Documentation Flask](https://flask.palletsprojects.com/)

## Obtenir de l'aide

Vous pouvez joindre l'équipe de développement Clue sur le discord CCCS aurora : <https://discord.gg/GUAy9wErNu>
