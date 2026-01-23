# Commencer

## Intégrer votre plugin dans Clue - Hébergement du code

Lors de la création d'un plugin, la première étape consiste à décider où le code sera stocké. Vous avez deux options
pour héberger le code :

### Inclure le plugin dans le dépôt Clue

Cette approche vous permet de développer le plugin en l'incluant dans le processus de construction de Clue, en
assurant qu'il est étroitement intégré avec les changements de schéma et les mises à jour de fonctionnalités des
packages de base de Clue. Cela permet aux développeurs de Clue de tester votre plugin pour la compatibilité, et
c'est actuellement l'approche recommandée.

**Note : Seuls les plugins Python sont actuellement pris en charge de cette manière !**

La première étape consiste à créer un dossier pour votre application dans le
[répertoire plugins](https://github.com/CybercentreCanada/clue/tree/develop/plugins). Vous pouvez utiliser les
scripts de configuration du makefile pour ce faire, ou copier un plugin existant selon vos préférences.

Une fois que vous avez terminé le développement des fonctionnalités principales, il est **fortement recommandé**
d'écrire au moins des tests unitaires très basiques pour votre plugin, la référence étant des tests d'intégration
complets contre des données simulées. Pour vous inspirer, consultez les plugins existants et leurs régimes de test.

#### Dépendances externes

Si vous importez des packages externes différents du modèle de plugin, vous devez les spécifier à la fois dans le
fichier `requirements.txt` de votre plugin et dans le groupe de dépendances des plugins du projet poetry. La commande
suivante peut le faire :

```bash
# Remplacez les dépendances ici par les vôtres
poetry add -G "<your-plugin>" azure-core 'azure-storage-blob>=12.2.0' 'azure-storage-file-datalake>=12.2.0'
```

#### Créer une Pull Request

Une fois que vous êtes satisfait de votre plugin, créez une pull request pour qu'un membre de l'équipe de
développement examine le plugin pour l'approbation finale. Certaines vérifications de qualité de code sont effectuées
sur le code - si des problèmes sont signalés, travaillez avec un membre de l'équipe de développement pour les
résoudre. Seules les vérifications de lisibilité et de compatibilité sont la responsabilité de l'équipe de
développement - nous n'avons aucun contrôle sur la fonctionnalité de votre plugin et ne pouvons pas aider au
développement de votre plugin au-delà des questions sur le code de base de Clue.

### Dépôt autonome

Si vous trouvez nos normes de code trop strictes ou insuffisantes, ou si vous souhaitez développer le plugin dans un
langage autre que Python, ou simplement ne voulez pas être inclus dans le dépôt, vous êtes libre d'héberger, tester
et construire le plugin dans un dépôt autonome. Nous recommandons d'exécuter des tests d'intégration avec une copie
de l'API Clue pour assurer la compatibilité.
