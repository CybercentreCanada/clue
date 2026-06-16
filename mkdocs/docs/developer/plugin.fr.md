# Créer un nouveau plugin Clue

Ce document vous guidera à travers le développement, la publication et le déploiement d'un nouveau plugin Clue.

## Configuration de l'environnement de développement

Utilisez cette section pour préparer votre machine afin de modifier et valider le code localement.
Ces étapes sont volontairement orientées pratique, pas une reproduction exacte de la CI.

### Prérequis

- Python 3.12+ et Poetry
- Docker (pour la pile de dépendances et les builds d'images)
- GNU Make

Références utiles :

- Documentation d'installation Poetry : <https://python-poetry.org/docs/#installation>
- Documentation CLI Poetry : <https://python-poetry.org/docs/cli/>
- Téléchargements Python : <https://www.python.org/downloads/>
- pyenv (gestionnaire optionnel de versions Python) : <https://github.com/pyenv/pyenv>
- Documentation d'installation Docker : <https://docs.docker.com/engine/install/>

### 1) Installer les dépendances du projet

Approche recommandée (à la racine du dépôt) :

```bash
make setup
```

Si `make setup` ne convient pas à votre environnement, installation manuelle :

```bash
cd api
python -m pip install poetry
poetry env use 3.12
poetry install --all-extras --with test
```

Si Poetry n'est pas disponible dans votre PATH après installation :

```bash
python -m pip install --user poetry
python -m poetry --version
```

Si vous utilisez pipx :

```bash
pipx install poetry
poetry --version
```

### 2) Préparer les dossiers locaux et la configuration Clue

Ces dossiers/fichiers de config sont généralement nécessaires pour le développement local API et plugin :

```bash
sudo mkdir -p /etc/clue/conf/
sudo mkdir -p /etc/clue/lookups/
sudo mkdir -p /var/log/clue/
sudo chmod a+rw /etc/clue/conf/
sudo chmod a+rw /etc/clue/lookups/
sudo chmod a+rw /var/log/clue/

cp api/build_scripts/classification.yml /etc/clue/conf/classification.yml
cp api/test/unit/config.yml /etc/clue/conf/config.yml
```

### 3) Démarrer les dépendances et lancer l'API en local

```bash
make start-dependencies
cd api
poetry run server
```

### 4) Exécuter les vérifications locales avant de pousser

Pour les changements API et interface plugin dans `api/` :

```bash
cd api
poetry check
poetry run ruff format clue --diff
poetry run ruff check clue
poetry run type_check
poetry run test
```

Pour les changements de Dockerfile dans `plugins/base/` :

```bash
hadolint plugins/base/base.Dockerfile
hadolint plugins/base/plugin.Dockerfile
hadolint plugins/base/debian.Dockerfile
```

### Dépannage de l'installation des dépendances

- Si Python 3.12 n'est pas disponible, installez-le d'abord (gestionnaire de paquets système, installateur officiel ou pyenv), puis relancez `poetry env use 3.12`.
- Si la résolution de l'environnement Poetry échoue, essayez de recréer l'environnement :

```bash
cd api
poetry env remove --all
poetry install --all-extras --with test
```

- Si les dépendances Docker ne démarrent pas, exécutez `docker compose ps` et `docker compose logs` depuis `api/dev/`.

## Création du plugin

Le moyen le plus simple de créer un plugin est d'utiliser l'assistant interactif. Ce script se trouve à
plugins/setup/create.py. Exécutez simplement le script Python et il vous demandera les informations requises :
```bash
python plugins/setup/create.py
```

## Interaction avec l'API centrale

### Initiation de la requête

Diverses applications clientes peuvent faire des requêtes à l'API centrale, qui à son tour transmettra les requêtes à
chaque plugin enregistré pertinent.

![Diagramme d'initiation de requête](https://mermaid.ink/img/pako:eNqFkk9PwkAQxb_KZrxoAgfg1oMJCokcTIjIRcphbId24_6p012RAN_dpaWxpqJ7mjf5vZmX7OwhsSlBBBtlt0mO7MTzJDYivAe7VcTL2aouxHK2Fv3-7WFqWCa5JuPEE717Kt3hzNa-cVmSflU7JQ0Fd1v-OaMNthM0-8fz2iwWxB_E1_fBzajEnWVCJcsTcNON8DNAM-TXBP8ProkqxVz5TJrBavqJulB01uJqsL6ADjvo8BI66qCjCoUeaGKNMg0_tj91YnA5aYohCmWK_BZDbI6BQ-_sYmcSiBx76gFbn-WN8EWKjiYSM0YN0QZVGboFmhdrvzWl0ll-rO-jOpPjF8rrveU?type=png)

### Réponse

Les réponses de chaque plugin sont ensuite fusionnées et renvoyées avec quelques métadonnées à l'application
cliente.

![Explication de la réponse](https://mermaid.ink/img/pako:eNqNkjFvwjAQhf-K5S6tBAPJlqESBaQyVEKlLCUMp_iSWLV90cUprQj_vYYEAaIDXnzv-d2nk847mZFCmcjc0DYrgb34mKZOhLMwTaHdaD37AVsZ7LV4GG3EcPjczhzrrLTovBg7Rx68JleLnPicbMUS-Rv5EhjdAKO7gdF_wPgGGN8NjK-BXf04CS0MRrwQIxhdi_Fi_nRETgKAjFbgUYkL_jvWVXjCVrzS1iCvu-vQuOnQvREgfbman0KrLiMH0iJb0CqsY3dwUulLtJjKJJQK-CuVqduHHDSelr8uk4nnBgeSqSnKk2iqw3hTDQWDlUkOpg5uBe6T6KxRaU_81i3_-Af2f73PsxQ?type=png)

## Opérations de plugin valides

### Enrichissement

Les enrichissements sont le pain et le beurre de Clue. Cela implique que l'utilisateur demande des informations
d'enrichissement sur un sélecteur donné en effectuant un appel réseau à l'API centrale, comme ceci :

```python
# Enrichissement d'un seul sélecteur
res = requests.get(
    f"{host}/api/v1/lookup/enrich/ip/127.0.0.1",
    params={"max_timeout": 2.0},
    headers={"Authorization": f"Bearer {access_token}"},
)

# Enrichissement en masse de sélecteurs
bulk_req = [{"type": "ip", "value": "127.0.0.1"}, {"type": "ip", "value": "127.0.0.2"}]

res = requests.post(
    f"{host}/api/v1/lookup/enrich",
    params={"max_timeout": 5.0, "sources": "test|bad"},
    headers={"Authorization": f"Bearer {access_token}"},
    json=bulk_req,
)
```

Pour un seul enrichissement, le corps de la réponse sera un `QueryResult` :

<details>
<summary>Exemple de QueryResult</summary>

```json
{
  "type": "ip",
  "value": "127.0.0.1",
  "source": "example_plugin",
  "error": null,
  "items": [
    {
      "classification": "TLP:CLEAR",
      "count": 23,
      "link": "https://example.com/moreinfo",
      "annotations": [
        {
          "analytic": "Assemblyline",
          "analytic_icon": "material-symbols:sound-detection-dog-barking",
          "author": null,
          "quantity": 10,
          "version": "1.0.0",
          "timestamp": "2024-12-16T12:54:26.374945+00:00",
          "type": "context",
          "value": "suspect",
          "confidence": 0.0,
          "severity": 0.0,
          "priority": 50.0,
          "summary": "Example summary of the information in this Annotation",
          "details": "# Here's some annotation details\\n\\nIt's very interesting",
          "link": "https://example.com/annotation",
          "icon": null,
          "ubiquitous": true
        },
        {
          "analytic": "Howler",
          "analytic_icon": null,
          "author": null,
          "quantity": 10,
          "version": "v0.0.1",
          "timestamp": "2024-12-30T12:54:26.374940+00:00",
          "type": "context",
          "value": "benign",
          "confidence": 1.0,
          "severity": 1.0,
          "priority": 50.0,
          "summary": "Example summary of the information in this Annotation",
          "details": null,
          "link": "https://example.com/annotation",
          "icon": null,
          "ubiquitous": true
        },
        {
          "analytic": "Assemblyline",
          "analytic_icon": null,
          "author": "John Smith",
          "quantity": 25,
          "version": "1.0.0",
          "timestamp": "2024-12-30T12:54:26.374940+00:00",
          "type": "mitigation",
          "value": 42.0,
          "confidence": 0.0,
          "severity": 0.5,
          "priority": 50.0,
          "summary": "Example summary of the information in this Annotation",
          "details": "# Here's some annotation details\\n\\nIt's very interesting",
          "link": null,
          "icon": null,
          "ubiquitous": false
        }
      ],
      "raw_data": {
        "id": 1,
        "raw_field": "some_data"
      }
    },
    {
      "classification": "TLP:CLEAR",
      "count": 9,
      "link": null,
      "annotations": [
        {
          "analytic": "Howler",
          "analytic_icon": "material-symbols:sound-detection-dog-barking",
          "author": null,
          "quantity": 10,
          "version": null,
          "timestamp": "2024-12-16T12:54:26.374945+00:00",
          "type": "frequency",
          "value": 42.0,
          "confidence": 0.5,
          "severity": 0.0,
          "priority": 50.0,
          "summary": "Example summary of the information in this Annotation",
          "details": null,
          "link": "https://example.com/annotation",
          "icon": null,
          "ubiquitous": true
        },
        {
          "analytic": null,
          "analytic_icon": null,
          "author": "John Smith",
          "quantity": 25,
          "version": "v0.0.1",
          "timestamp": "2024-12-30T12:54:26.374940+00:00",
          "type": "context",
          "value": "Involved in Operation Cat",
          "confidence": 1.0,
          "severity": 0.5,
          "priority": 1.0,
          "summary": "Example summary of the information in this Annotation",
          "details": null,
          "link": "https://example.com/annotation",
          "icon": null,
          "ubiquitous": false
        }
      ],
      "raw_data": [
        {
          "id": 1,
          "other_data": "example",
          "other_row": 45
        }
      ]
    },
    {
      "classification": "TLP:CLEAR",
      "count": 23,
      "link": "https://example.com/moreinfo",
      "annotations": [
        {
          "analytic": "Howler",
          "analytic_icon": null,
          "author": "John Smith",
          "quantity": 25,
          "version": "v0.0.1",
          "timestamp": "2024-12-30T12:54:26.374940+00:00",
          "type": "context",
          "value": "Involved in Operation Cat",
          "confidence": 1.0,
          "severity": null,
          "priority": 1000.0,
          "summary": "Example summary of the information in this Annotation",
          "details": null,
          "link": null,
          "icon": null,
          "ubiquitous": false
        },
        {
          "analytic": null,
          "analytic_icon": null,
          "author": null,
          "quantity": 25,
          "version": null,
          "timestamp": "2024-12-16T12:54:26.374945+00:00",
          "type": "frequency",
          "value": 42.0,
          "confidence": 0.0,
          "severity": null,
          "priority": 1000.0,
          "summary": "Example summary of the information in this Annotation",
          "details": "# Here's some annotation details\\n\\nIt's very interesting",
          "link": null,
          "icon": null,
          "ubiquitous": true
        }
      ],
      "raw_data": {
        "id": 1,
        "raw_field": "some_data"
      }
    }
  ],
  "maintainer": null,
  "datahub_link": "https://example.com/datahub",
  "documentation_link": null,
  "latency": 1470
}
```

</details>

Un enrichissement en masse renverra les données dans un dictionnaire de dictionnaires d'une liste de `QueryResult`,
où la première clé est le type et la deuxième clé est la valeur :

```json
{
    "ip": {
        "127.0.0.1": [
            // Voir ci-dessus pour un exemple complet de résultat de requête
            {
                "type": "ip",
                "value": "127.0.0.1",
                "source": "example_plugin",
                ...
            }
        ]
    }
}
```

Cependant, ce formatage est géré par l'API centrale et le plugin Clue pour la plupart.

### Actions

Les actions sont des opérations qu'un plugin peut effectuer sur un ou plusieurs sélecteurs. Par exemple, une action
pourrait ajouter un sélecteur à une base de données quelque part à des fins de suivi, renvoyer un résumé markdown de
résultats raffinés pour un ensemble de sélecteurs, ou toute autre action arbitraire. Clue n'impose que le format de
la réponse - il n'y a aucune restriction sur ce qu'une action peut faire.

Pour exécuter une action, l'utilisateur doit envoyer une demande d'exécution à l'API centrale :

```python
res = requests.post(
    f"{host}/api/v1/actions/execute/example/example_action",
    params={"max_timeout": 2.0},
    headers={"Authorization": f"Bearer {access_token}"},
    json={"selector": {"type": "ip", "value": "127.0.0.1"}, "other_choice": "b"},
)
```

Vous noterez le champ supplémentaire fourni. Nous l'expliquerons ensuite.

#### Paramètres supplémentaires

Les plugins Clue qui exposent une action peuvent demander des paramètres supplémentaires à l'utilisateur afin de
fournir le contexte de la demande d'action au plugin. Ces paramètres peuvent être déclarés du côté du plugin, et la
bibliothèque UI de Clue gérera la collecte des paramètres supplémentaires.

Les paramètres supplémentaires sont spécifiés à l'aide de génériques Python et de l'héritage de classes. Voici un
exemple correspondant à la demande ci-dessus :

```python
class Params(ExecuteRequest):
    other_value: Optional[str] = Field(description="Another field you should show", default="")
    choice: ChoiceEnum = Field(default=ChoiceEnum.a, description="Another choice for you")
    other_choice: ChoiceEnum = Field(description="Another choice for you with no default")

plugin = CluePlugin(
    ...,
    actions=[
        Action[Params](
            id="test_action",
            action_icon="codicon:terminal",
            name="Test Action",
            classification="TLP:CLEAR",
            summary="Tester",
            supported_types={"ip", "port", "sha256"},
            accept_multiple=True,
        )
    ]
)
```

Notez que les paramètres peuvent être marqués comme optionnels, comme indiqué ci-dessus - seul `other_choice` est
entièrement requis.

#### Résultats d'action

Afin de notifier l'utilisateur du résultat de l'action, les actions doivent renvoyer un modèle `ActionResult`. Cela
permet une brève description du résultat, la sortie de l'action (avec un format) ainsi qu'une énumération de statut :

```python
failed_example = ActionResult(
    outcome="failure",
    summary="Action failed.",
    format="markdown",
    output=textwrap.dedent(
        f"""
        # Action Failed

        Retaining your data was unsuccessful for an unknown reason.

        ## Error Message:

        {str(e)}
        """.strip()
    ),
)

success_example = ActionResult(
    outcome="success",
    summary="Action Completed Successfully",
    format="json",
    output={
        "example": "result"
    },
    link=Url("http://example.com"),
)
```

### Récupérateurs

Les récupérateurs sont un moyen pour les plugins de renvoyer des données au client à afficher en fonction d'un
sélecteur. Ces données peuvent être renvoyées dans n'importe quel format pris en charge - actuellement :

- Markdown
- Json
- Images

Les récupérateurs fonctionnent de manière similaire aux actions, sauf qu'aucune information supplémentaire ne peut
être fournie. Voici un exemple d'implémentation de récupérateur :

```python
def run_fetcher(fetcher: FetcherDefinition, selector: Selector, access_token: str | None) -> FetcherResult:
    "Fetch a rendering of the given email"
    try:
        if not access_token:
            return FetcherResult(outcome="failure", format="error", error="Missing access token.")

            # work here

            return FetcherResult(
                outcome="success",
                format="image",
                data=ImageResult(
                    image=f"data:image/png;base64,{base64.b64encode(image_data).decode("utf-8")}",
                    alt=f"Rendering of an image to do with the given selector",
                ),
            )
    except Exception as e:
        logger.exception("Error in run_fetcher")
        return FetcherResult.error_result(repr(e))

plugin = CluePlugin(
    ...,
    run_fetcher=run_fetcher,
)
```

## Construction de l'image Docker

Pour construire localement les images de base plugin depuis les Dockerfiles dans `plugins/base/` :

```bash
# Variante de base
docker build \
  -f plugins/base/base.Dockerfile \
  -t cccs/clue-plugin-base:local \
  .

# Variante Debian
docker build \
  -f plugins/base/debian.Dockerfile \
  -t cccs/clue-plugin-base:local-debian \
  .
```

Pour construire l'image API en local :

```bash
docker build \
  -f api/Dockerfile \
  -t clue-api:local \
  api
```

## Références supplémentaires

- Référence du workflow API : `.github/workflows/api-workflow.yml`
- Référence du workflow base plugin : `.github/workflows/base-plugin-workflow.yml`
- Guide de développement API : `docs/api/development.en.md`
