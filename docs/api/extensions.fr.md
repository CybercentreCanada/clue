# Extensions de l'API Clue

## Aperçu

Le système d'extensions de Clue vous permet d'ajouter des fonctionnalités personnalisées à l'API centrale sans modifier le code de base. Les extensions peuvent enregistrer de nouvelles routes API, ajouter des types de données personnalisés, intégrer des mécanismes d'authentification et effectuer des tâches d'initialisation au démarrage de l'application.

Les extensions sont chargées dynamiquement au démarrage en fonction de la configuration et peuvent s'intégrer de manière transparente à l'infrastructure existante de Clue.

## Fonctionnalités clés

Les extensions prennent en charge les capacités suivantes :

- **Routes API personnalisées** : Ajoutez de nouveaux points de terminaison API pour étendre les fonctionnalités de Clue
- **Hooks d'initialisation** : Exécutez du code lors du démarrage de l'application
- **Intégration d'authentification** : Implémentez l'échange de jetons On-Behalf-Of (OBO) pour les services externes
- **Types de données personnalisés** : Enregistrez de nouveaux types pris en charge avec des modèles de validation
- **Indicateurs de fonctionnalités** : Contrôlez le comportement de l'extension via des fonctionnalités configurables

## Structure d'extension

### Disposition de répertoire de base

```
my-extension/
├── __init__.py
├── config.py              # Configuration de l'extension
├── routes/                # Routes API personnalisées (optionnel)
│   └── my_route.py
├── obo.py                 # Module d'authentification OBO (optionnel)
└── extension.yml          # Fichier de configuration de l'extension
```

### Fichier de configuration de l'extension

Les extensions utilisent un fichier de configuration YAML pour définir leur comportement et leurs modules :

```yaml
name: "my-extension"

# Indicateurs de fonctionnalités optionnels
features:
  enable_feature_x: true
  enable_feature_y: false

# Modules optionnels
modules:
  # Fonction d'initialisation appelée au démarrage de l'application
  init: "my_extension.init:initialize"

  # Routes API personnalisées à enregistrer
  routes:
    - "my_route"  # Forme courte : sera préfixée avec le nom de l'extension
    # - "other_package.routes.custom_route"  # Forme complète : utilisée telle quelle

  # Module d'authentification OBO
  obo_module: true  # Forme courte : utilise <extension>.obo:get_obo_token
  # obo_module: "my_extension.auth:custom_obo"  # Forme complète : chemin personnalisé
```

### Classe de configuration de l'extension

Créez un fichier `config.py` dans votre extension :

```python
from pathlib import Path
from pydantic_settings import SettingsConfigDict
from clue.extensions.config import BaseExtensionConfig

class MyExtensionConfig(BaseExtensionConfig):
    model_config = SettingsConfigDict(
        yaml_file=Path(__file__).parent / "extension.yml",
        yaml_file_encoding="utf-8",
        strict=True
    )

# Exporter l'instance de configuration
config = MyExtensionConfig(name="my-extension")
```

## Types de modules

### 1. Module d'initialisation (init)

Le module d'initialisation est appelé une fois au démarrage de l'application Flask. Ceci est utile pour :

- Enregistrer des types de données personnalisés
- Établir des connexions aux services externes
- Configurer des ressources spécifiques à l'extension
- Effectuer des tâches de configuration uniques

**Signature de fonction :**

```python
def initialize(flask_app) -> None:
    """
    Initialise l'extension.

    Args:
        flask_app: L'instance de l'application Flask
    """
    pass
```

**Exemple :**

```python
# my_extension/init.py
from clue.constants.supported_types import add_supported_type
from clue.common.logging import get_logger

logger = get_logger(__file__)

def initialize(flask_app):
    """Initialise mon extension."""
    logger.info("Initialisation de my-extension")

    # Enregistrer des types de données personnalisés
    add_supported_type("ticket_id", r"^TICKET-\d{6}$")
    add_supported_type("custom_id", r"^\d{10}$", namespace="my-extension")

    # Effectuer d'autres initialisations
    logger.info("Mon extension initialisée avec succès")
```

### 2. Module de routes

Les routes vous permettent d'ajouter des points de terminaison API personnalisés à Clue. Les routes sont des Blueprints Flask qui sont enregistrés avec l'application principale.

**Exemple :**

```python
# my_extension/routes/my_route.py
from typing import Any
from clue.api import make_subapi_blueprint, ok
from clue.common.logging import get_logger

SUB_API = "myapi"
my_route = make_subapi_blueprint(SUB_API, api_version=1)
my_route._doc = "Mon API personnalisée"

logger = get_logger(__file__)

@my_route.route("/example", methods=["GET"])
def example_endpoint(**kwargs) -> tuple[dict[str, Any], int]:
    """
    Point de terminaison d'exemple.

    Returns:
        Réponse API avec statut de succès
    """
    # Votre logique personnalisée ici
    return ok({"message": "Bonjour de mon extension !"})

@my_route.route("/process/<data_id>", methods=["POST"])
def process_endpoint(data_id: str, **kwargs) -> tuple[dict[str, Any], int]:
    """
    Traiter les données par ID.

    Args:
        data_id: L'ID des données à traiter

    Returns:
        Réponse API avec résultats de traitement
    """
    # Votre logique de traitement personnalisée
    result = {"data_id": data_id, "status": "processed"}
    return ok(result)
```

Les routes seront disponibles à :
- `/api/v1/myapi/example`
- `/api/v1/myapi/process/<data_id>`

### 3. Module d'authentification OBO

Le module On-Behalf-Of (OBO) permet à votre extension d'implémenter une logique d'échange de jetons personnalisée pour accéder aux services externes au nom des utilisateurs.

**Signature de fonction :**

```python
def get_obo_token(service: str, access_token: str, user: str) -> str | None:
    """
    Échange un jeton d'accès pour un jeton OBO spécifique au service.

    Args:
        service: Le nom du service pour lequel obtenir un jeton
        access_token: Le jeton d'accès de l'utilisateur
        user: Le nom d'utilisateur

    Returns:
        Le jeton OBO pour le service, ou None si l'échange échoue
    """
    pass
```

**Exemple :**

```python
# my_extension/obo.py
import requests
from clue.common.logging import get_logger

logger = get_logger(__file__)

def get_obo_token(service: str, access_token: str, user: str) -> str | None:
    """Obtenir un jeton OBO pour le service spécifié."""
    try:
        if service == "my-external-service":
            # Implémentez votre logique d'échange de jetons OBO
            response = requests.post(
                "https://auth.example.com/obo/token",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"user": user, "service": service}
            )

            if response.status_code == 200:
                return response.json()["access_token"]
            else:
                logger.error("L'échange de jetons OBO a échoué : %s", response.text)
                return None

        # Laisser d'autres extensions ou le noyau gérer d'autres services
        return None

    except Exception as e:
        logger.exception("Exception lors de l'échange de jetons OBO pour %s : %s", service, e)
        return None
```

## Enregistrement de types de données personnalisés

Les extensions peuvent enregistrer des types de données personnalisés que Clue reconnaîtra et validera. Ceci est généralement effectué dans le module d'initialisation.

### Utilisation de add_supported_type

```python
from clue.constants.supported_types import add_supported_type

# Ajouter un type à l'espace de noms par défaut
add_supported_type("email", r"^[\w\.-]+@[\w\.-]+\.\w+$")

# Ajouter un type avec un espace de noms personnalisé
add_supported_type("custom_id", r"^\d{5}$", namespace="my-extension")
```

**Paramètres :**
- `type` (str) : Le nom du type à enregistrer
- `regex` (str | None) : Un modèle regex pour valider les valeurs de ce type (optionnel)
- `namespace` (str | None) : Un espace de noms pour regrouper le type (optionnel)

**Types avec espace de noms :**

Les types enregistrés avec un espace de noms sont stockés sous `namespace/type` (par exemple, `my-extension/custom_id`). Cela aide à éviter les conflits de nommage avec les types de base ou d'autres extensions.

**Types sans regex :**

Certains types ne nécessitent pas de validation de modèle. Définissez `regex=None` pour ces cas :

```python
add_supported_type("generic_id", regex=None)
```

## Activation des extensions

Les extensions sont activées via le fichier de configuration principal de Clue :

```yaml
# /etc/clue/conf/config.yml
core:
  extensions:
    - "my-extension"
    - "another-extension"
```

Lorsque Clue démarre, il va :

1. Rechercher un module nommé `my-extension`
2. Charger l'objet `config` depuis `my-extension.config`
3. Appeler la fonction `init` si elle est définie
4. Enregistrer toutes les routes spécifiées dans la configuration
5. Enregistrer le module OBO s'il est défini

## Processus de chargement des extensions

La séquence de chargement des extensions est la suivante :

1. **Chargement de la configuration** : Clue lit `core.extensions` depuis le fichier de configuration principal
2. **Importation de module** : Pour chaque extension, Clue importe `<nom-extension>.config`
3. **Validation** : La configuration YAML de l'extension est chargée et validée
4. **Initialisation** : Si un module `init` est défini, il est appelé avec l'application Flask
5. **Enregistrement des routes** : Toutes les routes définies dans l'extension sont enregistrées avec Flask
6. **Enregistrement OBO** : Si un `obo_module` est défini, il est enregistré pour l'échange de jetons

## Bonnes pratiques

### 1. Utiliser la journalisation appropriée

Utilisez toujours l'infrastructure de journalisation de Clue :

```python
from clue.common.logging import get_logger

logger = get_logger(__file__)

def my_function():
    logger.info("Traitement démarré")
    logger.error("Une erreur s'est produite : %s", error_message)
```

### 2. Gérer les erreurs avec élégance

Les échecs d'extension ne doivent pas faire planter l'application entière :

```python
def initialize(flask_app):
    try:
        # Votre logique d'initialisation
        setup_resources()
    except Exception as e:
        logger.exception("Échec de l'initialisation de l'extension : %s", e)
        # Ne pas relancer - permettre à Clue de continuer
```

### 3. Utiliser des espaces de noms pour les types personnalisés

Évitez les conflits de nommage en utilisant des types avec espace de noms :

```python
# Bon : Utilise un espace de noms
add_supported_type("user_id", r"^\d{8}$", namespace="my-extension")

# Risqué : Pourrait entrer en conflit avec le noyau ou d'autres extensions
add_supported_type("user_id", r"^\d{8}$")
```

### 4. Documenter votre extension

Incluez une documentation claire dans votre extension :

```python
"""
Mon extension pour Clue

Cette extension ajoute la prise en charge du traitement des ID de tickets personnalisés
et fournit une intégration avec le système de tickets externe.

Configuration :
    - feature_x : Activer la fonctionnalité expérimentale X

Routes :
    - GET /api/v1/tickets/status/<ticket_id>
    - POST /api/v1/tickets/create

Types personnalisés :
    - ticket_id : Format TICKET-######
    - case_id : Format CASE-########
"""
```

### 5. Tester votre extension

Créez des tests complets pour votre extension en suivant les modèles de la suite de tests de Clue :

```python
# test/test_my_extension.py
import pytest
from clue.extensions import EXTENSIONS

@pytest.fixture
def mock_extension():
    from my_extension.config import config
    EXTENSIONS["my-extension"] = config
    yield
    del EXTENSIONS["my-extension"]

def test_extension_initialization(mock_extension):
    """Tester que l'extension s'initialise correctement."""
    # Votre logique de test
    pass
```

## Exemple : Extension complète

Voici un exemple d'extension complète qui démontre toutes les fonctionnalités :

### Structure de répertoire

```
ticket_extension/
├── __init__.py
├── config.py
├── init.py
├── obo.py
├── extension.yml
└── routes/
    └── ticket_route.py
```

### extension.yml

```yaml
name: "ticket-extension"

features:
  enable_notifications: true
  enable_auto_assign: false

modules:
  init: "ticket_extension.init:initialize"
  routes:
    - "ticket_route"
  obo_module: true
```

### config.py

```python
from pathlib import Path
from pydantic_settings import SettingsConfigDict
from clue.extensions.config import BaseExtensionConfig

class TicketExtensionConfig(BaseExtensionConfig):
    model_config = SettingsConfigDict(
        yaml_file=Path(__file__).parent / "extension.yml",
        yaml_file_encoding="utf-8",
        strict=True
    )

config = TicketExtensionConfig(name="ticket-extension")
```

### init.py

```python
from clue.constants.supported_types import add_supported_type
from clue.common.logging import get_logger

logger = get_logger(__file__)

def initialize(flask_app):
    """Initialise l'extension de ticket."""
    logger.info("Initialisation de ticket-extension")

    # Enregistrer des types personnalisés
    add_supported_type("ticket_id", r"^TICKET-\d{6}$", namespace="ticket-extension")
    add_supported_type("case_id", r"^CASE-\d{8}$", namespace="ticket-extension")

    logger.info("Types de tickets personnalisés enregistrés")
    logger.info("Extension de ticket initialisée avec succès")
```

### routes/ticket_route.py

```python
from typing import Any
from clue.api import make_subapi_blueprint, ok, fail
from clue.common.logging import get_logger

SUB_API = "tickets"
ticket_route = make_subapi_blueprint(SUB_API, api_version=1)
ticket_route._doc = "API de gestion des tickets"

logger = get_logger(__file__)

@ticket_route.route("/status/<ticket_id>", methods=["GET"])
def get_ticket_status(ticket_id: str, **kwargs) -> tuple[dict[str, Any], int]:
    """
    Obtenir le statut d'un ticket.

    Args:
        ticket_id: L'ID du ticket à interroger

    Returns:
        Réponse API avec statut du ticket
    """
    # Votre logique pour récupérer le statut du ticket
    return ok({
        "ticket_id": ticket_id,
        "status": "open",
        "assignee": "analyst1"
    })

@ticket_route.route("/create", methods=["POST"])
def create_ticket(**kwargs) -> tuple[dict[str, Any], int]:
    """
    Créer un nouveau ticket.

    Returns:
        Réponse API avec détails du nouveau ticket
    """
    # Votre logique pour créer un ticket
    return ok({
        "ticket_id": "TICKET-123456",
        "status": "created"
    })
```

### obo.py

```python
import requests
from clue.common.logging import get_logger

logger = get_logger(__file__)

def get_obo_token(service: str, access_token: str, user: str) -> str | None:
    """Obtenir un jeton OBO pour les services du système de tickets."""
    if service != "ticket-system":
        return None

    try:
        response = requests.post(
            "https://tickets.example.com/auth/obo",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"user": user}
        )

        if response.status_code == 200:
            return response.json()["token"]
        else:
            logger.error("L'échange OBO a échoué : %s", response.text)
            return None

    except Exception as e:
        logger.exception("Exception lors de l'échange OBO : %s", e)
        return None
```

## Dépannage

### Extension ne se charge pas

Vérifiez les éléments suivants :

1. L'extension est listée dans `core.extensions` dans la configuration principale
2. Le module d'extension est dans le sys.path de Python
3. Le fichier `config.py` exporte un objet `config`
4. Vérifiez les journaux pour les erreurs d'importation

### Routes non accessibles

Vérifiez :

1. Les routes sont listées dans `modules.routes` de l'extension
2. Le module de route exporte un objet Blueprint
3. Vérifiez les journaux pour les messages "Enabling additional endpoint"
4. Assurez-vous de la structure d'URL appropriée (`/api/v1/<subapi>/<endpoint>`)

### Types personnalisés non reconnus

Assurez-vous que :

1. Les types sont enregistrés dans la fonction `init`
2. La fonction `init` est appelée (vérifiez les journaux)
3. Les modèles regex sont des regex Python valides
4. L'espace de noms est correctement spécifié s'il est utilisé

## Considérations de sécurité

### 1. Authentification

Les routes doivent valider l'authentification de l'utilisateur :

```python
from clue.security import requires_auth

@ticket_route.route("/sensitive", methods=["GET"])
@requires_auth()
def sensitive_endpoint(**kwargs):
    # Votre logique de point de terminaison protégé
    pass
```

### 2. Validation des entrées

Validez et nettoyez toujours les entrées :

```python
import re

@ticket_route.route("/process/<ticket_id>", methods=["GET"])
def process_ticket(ticket_id: str, **kwargs):
    # Valider le format
    if not re.match(r"^TICKET-\d{6}$", ticket_id):
        return fail("Format d'ID de ticket invalide"), 400

    # Traiter le ticket
    pass
```

### 3. Gestion des erreurs

N'exposez pas d'informations sensibles dans les messages d'erreur :

```python
try:
    result = external_api_call()
except Exception as e:
    logger.exception("L'appel API externe a échoué")
    return fail("Service temporairement indisponible"), 503
```

## Conseils de performance

### 1. Chargement paresseux

Chargez les ressources lourdes uniquement lorsque nécessaire :

```python
_heavy_resource = None

def get_heavy_resource():
    global _heavy_resource
    if _heavy_resource is None:
        _heavy_resource = load_heavy_resource()
    return _heavy_resource
```

### 2. Mise en cache

Utilisez l'infrastructure de mise en cache de Clue :

```python
from clue.cache import cache

@cache.memoize(timeout=300)
def expensive_operation(param):
    # Votre opération coûteuse
    pass
```

### 3. Tâches en arrière-plan

Pour les opérations de longue durée, envisagez d'utiliser des tâches en arrière-plan ou des files d'attente plutôt que de bloquer les requêtes API.

## Référence de l'API

### BaseExtensionConfig

Classe de base pour la configuration de l'extension.

**Attributs :**
- `name` (str) : Nom de l'extension
- `features` (dict[str, bool]) : Indicateurs de fonctionnalités
- `modules` (Modules) : Configuration des modules d'extension

### Modules

Configuration des modules d'extension.

**Attributs :**
- `init` (ImportString | None) : Fonction d'initialisation
- `routes` (list[ImportString]) : Liste des modules de routes
- `obo_module` (ImportString | None) : Module d'authentification OBO

### add_supported_type

Enregistrer un type de données personnalisé.

```python
def add_supported_type(
    type: str,
    regex: str | None = None,
    namespace: str | None = None
) -> None
```

**Paramètres :**
- `type` : Nom du type
- `regex` : Modèle regex de validation (optionnel)
- `namespace` : Espace de noms du type (optionnel)

## Ressources supplémentaires

- [Guide de développement de l'API Clue](development.fr.md)
- [Guide de développement de plugins](../../plugins/)
- [Exemples de tests](../../api/test/integration/extensions/)
