# Créer un nouveau plugin Clue

## Introduction

Clue vise à fonctionner comme une sorte de tissu de connexion entre les applications. Initialement envisagée comme une plateforme d'enrichissement, sa fonctionnalité s'est élargie pour permettre également l'exécution d'actions par le biais d'une interface unifiée, et
comprendra éventuellement la récupération de représentations de données (c'est-à-dire des rendus d'e-mails, des arbres de processus pour un hôte, etc.)

Pour ce faire, borealis s'appuie sur une architecture de plugins, où les services sont configurés de telle sorte que borealis
sache qu'il faut faire appel à un plugin donné dans diverses circonstances. Par exemple, une demande d'exécution de l'action
`example_plugin.example_action` serait dirigée vers le plugin avec l'identifiant `example_plugin`. Pour l'enrichissement, le serveur central
demande à tous les plugins concernés de fournir des annotations d'enrichissement pour un sélecteur donné.

Ce document vous guidera dans le développement, la publication et le déploiement d'un nouveau plugin borealis.

## Conception

L'approche "par défaut" des plugins borealis consiste à exécuter un serveur flask dans un pod sur l'espace de noms dédié à borealis, et
pour que la communication entre les plugins se fasse en interne dans le cluster. Cependant, les plugins peuvent être hébergés à n'importe quel endroit accessible par le serveur central à l'adresse. Le processus d'exécution d'une application ressemble à ceci:

### Initiation de la demande

Diverses applications clientes peuvent adresser des demandes à l'API centrale qui, à son tour, transmettra les demandes à chaque plugin enregistré pertinent.

![Request Initiation Diagram](https://mermaid.ink/img/pako:eNqFkk9PwkAQxb_KZrxoAgfg1oMJCokcTIjIRcphbId24_6p012RAN_dpaWxpqJ7mjf5vZmX7OwhsSlBBBtlt0mO7MTzJDYivAe7VcTL2aouxHK2Fv3-7WFqWCa5JuPEE717Kt3hzNa-cVmSflU7JQ0Fd1v-OaMNthM0-8fz2iwWxB_E1_fBzajEnWVCJcsTcNON8DNAM-TXBP8ProkqxVz5TJrBavqJulB01uJqsL6ADjvo8BI66qCjCoUeaGKNMg0_tj91YnA5aYohCmWK_BZDbI6BQ-_sYmcSiBx76gFbn-WN8EWKjiYSM0YN0QZVGboFmhdrvzWl0ll-rO-jOpPjF8rrveU?type=png)

### Réponse

Les réponses de chaque plugin sont ensuite fusionnées et renvoyées avec certaines métadonnées à l'application cliente.

![Response Explanation](https://mermaid.ink/img/pako:eNqNkjFvwjAQhf-K5S6tBAPJlqESBaQyVEKlLCUMp_iSWLV90cUprQj_vYYEAaIDXnzv-d2nk847mZFCmcjc0DYrgb34mKZOhLMwTaHdaD37AVsZ7LV4GG3EcPjczhzrrLTovBg7Rx68JleLnPicbMUS-Rv5EhjdAKO7gdF_wPgGGN8NjK-BXf04CS0MRrwQIxhdi_Fi_nRETgKAjFbgUYkL_jvWVXjCVrzS1iCvu-vQuOnQvREgfbman0KrLiMH0iJb0CqsY3dwUulLtJjKJJQK-CuVqduHHDSelr8uk4nnBgeSqSnKk2iqw3hTDQWDlUkOpg5uBe6T6KxRaU_81i3_-Af2f73PsxQ?type=png)

## Opérations de plugin valides

### Enrichissement

Les enrichissements sont la spécialité de borealis. Cela implique que l'utilisateur demande des informations d'enrichissement sur un sélecteur
donné en effectuant un appel réseau à l'API centrale, comme suit:

```python
# Enriching a single selector
res = requests.get(
    f"{host}/api/v1/lookup/enrich/ip/127.0.0.1",
    params={"max_timeout": 2.0},
    headers={"Authorization": f"Bearer {access_token}"},
)

# Bulk enrichment of selectors
bulk_req = [{"type": "ip", "value": "127.0.0.1"}, {"type": "ip", "value": "127.0.0.2"}]

res = requests.post(
    f"{host}/api/v1/lookup/enrich",
    params={"max_timeout": 5.0, "sources": "test|bad"},
    headers={"Authorization": f"Bearer {access_token}"},
    json=bulk_req,
)
```

Pour un seul enrichissement, le corps de la réponse sera un `QueryResult`:

<details>
<summary>QueryResult Example</summary>

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

Un enrichissement en masse renverra les données dans un dict de dicts d'une liste de `QueryResult`s, où la première clé est le type
et la deuxième clé est la valeur:

```json
{
    "ip": {
        "127.0.0.1": [
            // See above for a full query result example
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

Cependant, ce formatage est en grande partie géré par l'API centrale et le plugin borealis.

### Actions

Les actions sont des opérations qu'un plugin peut effectuer sur un ou plusieurs sélecteurs. Par exemple, une action peut ajouter
un sélecteur à une base de données quelque part à des fins de suivi, renvoyer un résumé des résultats affinés pour un ensemble de sélecteurs
, ou toute autre action arbitraire. Clue n'impose que le format de la réponse - il n'y a aucune restriction
sur ce qu'une action peut faire.

Pour exécuter une action, l'utilisateur doit envoyer une demande d'exécution à l'API centrale :

```python
res = requests.post(
    f"{host}/api/v1/actions/execute/example/example_action",
    params={"max_timeout": 2.0},
    headers={"Authorization": f"Bearer {access_token}"},
    json={"selector": {"type": "ip", "value": "127.0.0.1"}, "other_choice": "b"},
)
```

Vous remarquerez le champ supplémentaire prévu. Nous l'expliquerons plus loin.

#### Paramètres supplémentaires

Les plugins Clue qui exposent une action peuvent demander des paramètres supplémentaires à l'utilisateur afin de fournir le contexte de
la demande d'action au plugin. Ces paramètres peuvent être déclarés du côté du plugin, et la bibliothèque borealis UI se chargera
de rassembler les paramètres supplémentaires.

Les paramètres supplémentaires sont spécifiés à l'aide de Python Generics et de l'héritage de classes. Voici un exemple correspondant à
la requête ci-dessus :

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

Notez que les paramètres peuvent être marqués comme optionnels, comme indiqué ci-dessus - seul `other_choice` est entièrement requis.

#### Action Results

Afin d'informer l'utilisateur du résultat de l'action, les actions doivent renvoyer un modèle `ActionResult`. Ce modèle
permet une courte description du résultat, la sortie de l'action (avec un format) ainsi qu'un enum de statut :

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

### Les récupérateurs

Les récupérateurs sont un moyen pour les plugins de renvoyer au client des données qui seront affichées en fonction d'un sélecteur. Ces données peuvent être renvoyées à l'adresse
dans n'importe quel format de support - actuellement :

- Markdown
- Json
- Images

Le fonctionnement des récupérateurs est similaire à celui des actions, à ceci près qu'aucune information supplémentaire ne peut être fournie. Vous trouverez ci-dessous un exemple de mise en œuvre de récupérateurs :

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

## Intégration de votre plugin dans Clue - Responsabilités et attentes

Étant donné que borealis est un projet relativement complexe qui comporte un grand nombre de pièces mobiles, il est important de définir les responsabilités des différentes parties prenantes sur le site :

1. APA2B est le principal propriétaire du code de borealis-api (c'est-à-dire tout le code contenu dans le dossier `borealis/`).
2. Chaque équipe est responsable de la maintenance et de l'évolution de son plugin spécifique.
3. Chaque équipe est responsable de la compatibilité entre son plugin et l'API centrale.
   1. Il s'agit notamment de s'adapter aux ruptures introduites au cours du développement du service de base borealis.
   2. L'APA2B s'efforcera de limiter autant que possible ces changements radicaux et de les annoncer suffisamment à l'avance.
4. L'APA2B est disponible pour apporter son soutien au développement (poser des questions, corriger des bogues dans le service central, etc.)
5. L'APA2B est responsable du maintien de la stabilité du service dans son ensemble.

## Intégrer votre plugin dans Clue - Héberger le code

Lorsque vous créez un plugin, la première étape consiste à décider de l'endroit où le code sera stocké. Vous avez deux options pour héberger le code de :

### Inclure le plugin dans le repo

Cette approche vous permet de développer le plugin, en l'incluant dans le processus de construction de borealis, en veillant à ce qu'il soit étroitement intégré à
avec les changements de schéma et les mises à jour de fonctionnalités au sommet des paquets de base de borealis. Cela permet aux développeurs de borealis de tester
la compatibilité de votre plugin, et c'est actuellement l'approche recommandée.

**Note : Seuls les plugins python sont actuellement pris en charge de cette manière!**

La première étape consiste à créer un dossier pour votre application dans le répertoire
[plugins directory](https://github.com/CybercentreCanada/borealis-api/tree/develop/plugins). Vous pouvez utiliser le
[borealis example template](https://github.com/CybercentreCanada/borealis-plugin-template/) pour le faire, ou copier un plugin existant
en fonction de vos préférences.

Une fois que vous avez terminé le développement des fonctionnalités de base, il est **fortement recommandé** d'écrire au moins
des tests unitaires de base pour votre plugin, la norme d'excellence en la matière étant un test d'intégration complet avec des données fictives. Pour vous inspirer de, consultez les plugins existants et leurs régimes de test.

Vous devez également ajouter une entrée au
[`azure-pipelines.yml`](https://github.com/CybercentreCanada/borealis-api/blob/develop/azure-pipelines.yml#L277)
à la racine du projet de votre application.

Pour des informations détaillées sur l'initialisation des tests, voir notre site principal [README](../README.md) de l'APA2B. Pour obtenir un soutien supplémentaire, adressez-vous à l'APA2B à l'adresse.

#### Dépendances externes

Si vous importez des paquets externes différents du modèle de plugin, vous devez les spécifier à la fois dans le fichier `requirements.txt`
de votre plugin, et dans le groupe de dépendances du plugin du projet poetry. La commande suivante permet de le faire :

```bash
# Replace the dependencies here with yours
poetry add -G plugins azure-core 'azure-storage-blob>=12.2.0' 'azure-storage-file-datalake>=12.2.0'
```

#### Création d'une Pull Request

Une fois que vous êtes satisfait de votre plugin, créez une pull request pour qu'un membre de l'APA2B révise le plugin pour l'approbation finale.
Certains contrôles de la qualité du code sont effectués sur la base de code - si des problèmes sont signalés, travaillez avec un membre de
APA2B pour les résoudre. Seuls les contrôles de lisibilité et de compatibilité relèvent de la responsabilité de l'APA2B - nous n'avons aucun droit de regard sur
la fonctionnalité de votre plugin et nous ne pouvons pas vous aider à développer votre plugin au-delà des questions relatives à la base de code
borealis.

### Repo autonome

Si vous trouvez nos normes de code trop strictes ou insuffisantes, ou si vous voulez développer le plugin dans un langage autre que
python, ou si vous ne voulez tout simplement pas être inclus dans le dépôt, vous êtes invité à héberger, tester et construire le plugin dans
un dépôt autonome. Nous recommandons d'effectuer des tests d'intégration avec une copie de l'API borealis pour garantir la compatibilité avec celle-ci.

## Déployer le plugin

Actuellement, le déploiement des plugins dans l'espace de noms d'enrichissement relève de la responsabilité de l'APA2B - il n'existe aucune ressource sur
permettant aux développeurs de déployer et de supprimer manuellement leurs plugins. Cependant, le plugin peut exister partout où l'API centrale
borealis peut être atteinte, il n'est donc pas nécessaire de le déployer dans cet espace de noms.

Si votre code est hébergé dans ce repo, l'APA2B vous aidera à configurer et à déployer votre plugin lorsqu'il sera prêt pour la production sur.
Il est prévu d'améliorer la gestion des plugins, y compris leur déploiement dans l'espace de noms d'enrichissement
sans l'intervention de l'APA2B, mais la mise en œuvre de cette mesure prendra un certain temps et le travail n'est pas prévu pour l'instant.

## Enregistrer le plugin

Si vous hébergez le code de votre plugin dans ce repo, la construction de l'image et son déploiement seront de la responsabilité de l'APA2B -
sinon, c'est la responsabilité des développeurs du plugin.

Actuellement, l'enregistrement des plugins auprès de l'API centrale de borealis est principalement géré par les fichiers de configuration
dans les charts de Helm. Il existe un support pour l'enregistrement des plugins au moment de l'exécution, mais il est assez basique - contactez l'APA2B si
vous êtes intéressé par l'enregistrement au moment de l'exécution.

## Guide de développement des plugins

### Installer la poetry

```bash
pip install poetry
cd borealis-api
poetry install --with dev,test --all-extras

poetry run pre-commit install

poetry run server
```

#### Commandes utiles

Pour activer un venv, utilisez **`poetry shell`**.

Pour ajouter une nouvelle dépendance, utilisez **`poetry add`** :

```bash
➜  borealis-api git:(poetry) poetry add pyjwt
Using version ^2.8.0 for pyjwt

Updating dependencies
Resolving dependencies... (0.5s)

Package operations: 1 install, 0 updates, 0 removals

  - Installing pyjwt (2.8.0)

Writing lock file
```

Puis livrer les nouveaux `pyproject.toml` et `poetry.lock`.

### Configuration et dossiers Clue

```bash
# Clue config.yml should be in this location, as well as classification.yml
# For a starter config, use the test config.yml and classification.
sudo mkdir -p /etc/borealis/conf
# Log file directory, will write log files here if enabled
sudo mkdir -p /var/log/borealis

sudo chown -R $USER /etc/borealis
sudo chown $USER /var/log/borealis
```
