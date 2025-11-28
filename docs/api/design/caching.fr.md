# La mise en cache dans Clue

Clue met en œuvre une architecture de mise en cache multicouche pour optimiser les performances et réduire les demandes d'enrichissement redondantes.
Le système de mise en cache fonctionne à la fois au niveau du client (IU) et du serveur (API/Plug-ins), assurant un stockage et une récupération efficaces des données entre les différents composants.

## Guide de l'utilisateur : FAQ sur la mise en cache

Cette section répond aux questions courantes des analystes et des utilisateurs concernant la persistance et la fraîcheur des données.

### Mes données sont-elles sauvegardées ?

**Non.** Clue utilise le **stockage de session**, ce qui signifie que vos données d'enrichissement ne persistent que tant que votre onglet de navigateur est ouvert.
**Avertissement :** Si vous fermez votre onglet ou votre fenêtre, tous vos résultats d'enrichissement actuels seront perdus.

### Combien de temps les données restent-elles « fraîches » ?

Par défaut, les plug-ins mettent en cache les résultats pendant **5 minutes**. Si vous recherchez le même indicateur dans ce laps de temps, vous verrez le résultat mis en cache. Après 5 minutes, Clue récupérera automatiquement de nouvelles données à partir de la source.

### Comment obtenir de nouvelles données immédiatement ?

Si vous pensez que les données ont changé (par exemple, une mise à jour de la réputation d'une adresse IP), vous pouvez forcer une actualisation :

1. Dans l'interface utilisateur de Clue, recherchez l'option **« Sauter le cache du plugin »**.
2. Activez cette option avant de soumettre votre demande.
3. Cela signale au serveur d'ignorer tout cache existant et de récupérer des données en direct à partir de la source.

### Pourquoi est-ce plus rapide la deuxième fois ?

Lorsque vous consultez un résultat que vous avez déjà enrichi dans votre session actuelle, il se charge instantanément car il est stocké dans le cache local de votre navigateur (mise en cache côté client).

## Aperçu

L'architecture de mise en cache se compose de trois couches principales :

1. **Mise en cache côté client** : Stockage basé sur le navigateur pour la persistance des données de l'IU.
2. **Mise en cache côté plug-in** : Mise en cache côté serveur (Redis ou locale) au sein des plug-ins individuels.
3. **Contrôles de contournement du cache** : Mécanismes pour forcer la récupération de données fraîches lorsque nécessaire.

## Mise en cache côté client (IU)

L'interface utilisateur de Clue utilise une base de données réactive côté client (RxDB) pour stocker vos données pendant que vous travaillez. Cela permet des mises à jour en temps réel et des capacités hors ligne.

### Stockage de session (Persistance des données)

**Important :** L'IU utilise le **stockage de session**, ce qui signifie :

* **Persistance à l'échelle de la session** : Les données ne persistent que pour la session du navigateur.
* **Nettoyage automatique** : Les données sont effacées lorsque l'onglet ou la fenêtre du navigateur est fermé.
* **Isolation inter-onglets** : Chaque onglet du navigateur maintient son propre cache.

<details>
<summary>Implémentation technique : Configuration RxDB</summary>

La base de données de l'IU est configurée pour utiliser le stockage de session comme backend.

```typescript
// Configuration du stockage avec backend de stockage de session
storage: wrappedKeyCompressionStorage({
  storage: wrappedValidateAjvStorage({
    storage: getRxStorageLocalstorage({ localStorage: sessionStorage })
  })
})
```

</details>

### Collections de données

La base de données gère deux types principaux de données :

1. **Sélecteurs** : Stocke les résultats d'enrichissement, les annotations et les données de classification.
2. **Statut** : Suit l'état des demandes (`pending`, `in-progress`, `complete`) pour gérer les files d'attente et éviter les doublons.

<details>
<summary>Implémentation technique : Collections</summary>

#### Collection de sélecteurs

* Schéma : `selector.schema.json`
* Indexé par type, valeur et classification pour une interrogation efficace
* Gère automatiquement la compression et la validation des données

#### Collection de statuts

* Permet la gestion de la file d'attente pour les opérations d'enrichissement en masse
* Empêche les demandes en double en vérifiant les enregistrements de statut existants

</details>

### Flux de travail d'enrichissement

Lorsque vous demandez des données d'enrichissement, le système suit un flux de travail structuré pour éviter les demandes en double et gérer les données efficacement :

1. **Vérification du statut** : Le système vérifie d'abord si l'enrichissement est déjà en cours ou terminé.
2. **Mise en file d'attente des demandes** : Les nouvelles demandes sont mises en file d'attente avec un suivi de statut approprié.
3. **Stockage des données** : Les résultats sont automatiquement stockés dans la base de données locale pour une utilisation future.

<details>
<summary>Implémentation technique</summary>

```typescript
// 1. Vérifier le statut existant pour éviter les doublons
let statusRecord = await database.status
  .findOne({ selector: { type, value, classification } })
  .exec();

// 2. Créer ou mettre à jour l'enregistrement de statut
if (!statusRecord) {
  statusRecord = await database.status.insert({
    id: uuid(),
    type, value, classification,
    status: 'pending'
  });
}

// 3. Mettre en file d'attente l'enrichissement et stocker les résultats
const enrichmentResult = await lookup.enrich.post([selector], sources, options);
await _addEntries(Object.values(enrichData));
```

</details>

### Gestion de la file d'attente

Le client met en œuvre une gestion intelligente de la file d'attente pour optimiser les performances :

* **Traitement différé (Debounced)** : Les demandes d'enrichissement sont regroupées et traitées avec un délai de 200 ms.
* **Demandes par lots (Chunked)** : Les grands lots sont divisés en morceaux configurables (par défaut : 15 sélecteurs).
* **Limites de concurrence** : Le nombre maximum de demandes simultanées est contrôlé (par défaut : 4 demandes).
* **Nouvelle tentative manuelle** : Les enrichissements échoués peuvent être retentés sur demande de l'utilisateur via la fonctionnalité de nouvelle tentative.

## Mise en cache côté plug-in

Les plug-ins utilisent la mise en cache côté serveur pour améliorer les temps de réponse. Cela signifie que si vous ou un collègue recherchez le même indicateur, le système peut renvoyer le résultat précédent au lieu d'interroger à nouveau le service externe.

### Types de cache et cohérence

Le système peut être configuré de deux manières, ce qui affecte la façon dont les données sont partagées entre les utilisateurs :

1. **Mise en cache Redis (Partagé)** : Le cache est partagé dans tout le système. Si vous enrichissez un indicateur, votre collègue verra le résultat mis en cache immédiatement.
2. **Mise en cache mémoire locale (Isolé)** : Chaque unité de traitement (« worker ») possède son propre cache.

**Note pour l'analyste (Dépannage) :**
Si vous et un collègue voyez des résultats différents pour le même indicateur au même moment, votre système utilise peut-être la **Mise en cache locale**. Dans ce mode, vous pourriez atteindre un worker qui a des données anciennes, tandis que votre collègue atteint un worker avec de nouvelles données.

<details>
<summary>Implémentation technique : Types de cache</summary>

#### Mise en cache Redis

Redis fournit une mise en cache distribuée partagée entre tous les workers de plug-in et les pods dans un cluster Kubernetes.

```python
# Utilise ExpiringHash pour la mise en cache distribuée
self.__redis_cache = ExpiringHash(cache_name, host=get_redis(), ttl=timeout)
```

#### Mise en cache mémoire locale

La mise en cache mémoire locale stocke les données au sein des workers de plug-in individuels. Dans les déploiements Kubernetes, chaque worker maintient son propre cache indépendant.

```python
# Utilise Flask-Caching avec le backend SimpleCache
self.__local_cache = FlaskCache(app, config={
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": timeout
})
```

</details>

### Clés de cache

Le système garantit que différents types de demandes pour le même indicateur sont mis en cache séparément. Par exemple, une demande demandant des « données brutes » sera mise en cache séparément d'une demande qui ne le fait pas.

<details>
<summary>Implémentation technique : Génération de clés</summary>

Les clés de cache sont générées en utilisant le hachage SHA256 de :

* Type et valeur du sélecteur
* Paramètres d'inclusion d'annotations
* Paramètres d'inclusion de données brutes
* Paramètres de limite de résultat

```python
def __generate_hash(self, type_name: str, value: str, params: Params) -> str:
    hash_data = sha256(type_name.encode())
    # ... logique de hachage ...
    return hash_data.hexdigest()
```

</details>

## Contrôles de contournement du cache

Parfois, vous devez vous assurer de voir les données les plus récentes, en ignorant les résultats mis en cache.

### Utilisation de l'IU (Sauter le cache du plugin)

Pour forcer une nouvelle recherche :

1. Localisez l'option **« Sauter le cache du plugin »** dans l'interface.
2. Activez-la avant de soumettre votre demande.
3. Cela envoie un signal au serveur pour ignorer tout cache existant et récupérer de nouvelles données à partir de la source.

<details>
<summary>Implémentation technique : API et Client</summary>

#### Contrôle du cache au niveau de l'API

L'API prend en charge le contournement du cache via le paramètre `no_cache`.

```python
# Analyse des paramètres de requête
no_cache = request.args.get("no_cache", "false").lower() in ("true", "1", "")
```

#### Contrôle du cache côté client

L'IU envoie ce paramètre lorsque l'option est sélectionnée.

```typescript
const options = {
  noCache: true,  // Contourner le cache du plugin
  force: true,    // Forcer une nouvelle demande d'enrichissement
};
```

</details>

## Considérations de performance

### Optimisations côté client

* **Mises à jour réactives** : RxDB fournit des mises à jour de l'IU en temps réel lorsque de nouvelles données arrivent.
* **Traitement par lots intelligent** : Les demandes sont automatiquement regroupées pour réduire les appels API.
* **Suivi du statut** : Empêche les demandes en double pour le même sélecteur.
* **Gestion de la mémoire** : Le stockage de session se nettoie automatiquement à la fermeture de l'onglet.

### Optimisations côté plug-in

* **TTL configurable** : Le délai d'expiration du cache peut être ajusté par plug-in (par défaut : 5 minutes).
* **Sérialisation** : Sérialisation JSON efficace avec les modèles Pydantic.
* **Gestion des erreurs** : Repli gracieux lorsque les opérations de cache échouent.
* **Compression des clés** : RxDB utilise la compression des clés pour réduire la surcharge de stockage.

## Invalidation du cache

### Invalidation automatique

* **Expiration TTL** : Les entrées de cache expirent automatiquement après le délai configuré.
* **Fin de session** : Le cache côté client est effacé lorsque la session du navigateur se termine.
* **Réinitialisation du statut** : Les demandes en cours sont effacées au démarrage de l'application.

### Invalidation manuelle

* **Cache du plug-in** : Les entrées de cache individuelles peuvent être supprimées en utilisant `cache.delete()`.
* **Cache client** : Les enrichissements échoués peuvent être effacés et retentés.
* **Contournement API** : Le paramètre `no_cache` force la récupération de données fraîches.

## Exemples de configuration

### Configuration du cache du plug-in

Les plug-ins peuvent être configurés pour utiliser soit Redis (recommandé pour la production), soit la mise en cache mémoire locale.

<details>
<summary>Exemples de configuration</summary>

```python
# Mise en cache Redis avec TTL de 10 minutes
plugin = CluePlugin(
    app_name="example-plugin",
    enable_cache="redis",
    cache_timeout=10 * 60
)

# Mise en cache mémoire locale
plugin = CluePlugin(
    app_name="example-plugin",
    enable_cache="local",
    local_cache_options={"CACHE_TYPE": "SimpleCache"}
)
```

</details>

### Configuration de la base de données de l'IU

La base de données de l'IU peut être configurée pour différents environnements et cas d'utilisation.

<details>
<summary>Exemples de configuration</summary>

```typescript
// Production : Stockage de session avec compression
const config: DatabaseConfig = {
  storageType: 'session',
  devMode: false
};

// Test : Stockage mémoire sans compression
const config: DatabaseConfig = {
  storageType: 'memory',
  devMode: true,
  testing: true
};
```

</details>

Cette architecture de mise en cache multicouche assure des performances optimales tout en offrant une flexibilité pour différents scénarios de déploiement et cas d'utilisation.
