# Tester Clue dans une autre application

## Le problème

Lors de l'intégration de Clue-UI dans une autre application et de l'écriture de tests unitaires avec Jest et React
Testing Library, vous pouvez rencontrer des échecs de test en raison de la façon dont la bibliothèque gère son état
interne et ses connexions à la base de données.

### Cause principale

Le problème principal provient du **rendu continu de l'ensemble du ClueProvider** pendant l'exécution des tests. Bien
que cette approche fonctionne bien pour la plupart des composants et fonctions React sans état, elle crée des
problèmes importants lors du travail avec **RxDB** (Reactive Database), qui est utilisé en interne par Clue-UI pour
la gestion des données.

### Pourquoi RxDB a des difficultés avec les rendus répétés

RxDB maintient des connexions de base de données persistantes et des abonnements réactifs. Lorsque le ClueProvider
est recréé pour chaque test (un modèle courant dans React Testing Library), plusieurs problèmes se produisent :

1. **Conflits de connexion à la base de données** : Plusieurs instances de base de données tentant d'accéder au même
   stockage peuvent entraîner des problèmes de verrouillage
2. **Fuites de mémoire** : Les instances de base de données précédentes peuvent ne pas être correctement nettoyées
   avant que de nouvelles ne soient créées
3. **Gestion des abonnements** : Les abonnements réactifs de RxDB peuvent persister au-delà des limites des tests,
   causant des effets secondaires inattendus
4. **Problèmes de timing asynchrones** : L'initialisation de la base de données est asynchrone, et une recréation
   rapide peut entraîner des conditions de course

### Modèles d'échec de test courants

Vous pourriez voir des erreurs comme :

- Délais d'expiration de connexion à la base de données
- Erreurs "Database already exists"
- Tests qui réussissent individuellement mais échouent lorsqu'ils sont exécutés dans une suite
- Échecs intermittents difficiles à reproduire
- Utilisation de la mémoire qui continue de croître à travers les exécutions de tests

## La solution

Pour atténuer cela, il est préférable de créer une **instance statique de la base de données** et de passer la même
instance entre les tests/rendus. Cela garantit une gestion cohérente de l'état et empêche les problèmes de connexion
à la base de données décrits ci-dessus.

À titre d'exemple, tiré de [`enrich.test.tsx`](../src/lib/hooks/enrich.test.tsx) :

```tsx
// Initialiser la base de données de test
const database = await buildDatabase({ devMode: false, storageType: 'memory' });

// Composant wrapper de test qui fournit le contexte d'enrichissement
const Wrapper = ({ children }) => {
  return (
    <ClueProvider
      ready
      database={database}
      getToken={getToken}
      onNetworkCall={onNetworkCall}
      pickSources={pickSources}
      chunkSize={ENRICH_CHUNK_SIZE}
      debugLogging={!!process.env.ENABLE_DEBUG_LOGGNIG}
      config={MOCK_RESPONSES['/api/v1/configs']}
      skipConfigCall
    >
      {children}
    </ClueProvider>
  );
};

describe('enrich functionality', () => {
  it('should return the expected list of available sources', async () => {
    const { result } = await act(async () => {
      return renderHook(() => useClueEnrichSelector(ctx => ctx.availableSources), { wrapper: Wrapper });
    });

    expect(result.current).toEqual(['example', 'potato']);
  });
});
```
