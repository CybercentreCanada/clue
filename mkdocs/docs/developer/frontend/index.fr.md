# Guide de développement de l'interface utilisateur Clue

Ce guide explique comment configurer un environnement de développement pour l'interface utilisateur Clue.

## Prérequis

Avant de commencer, assurez-vous d'avoir les éléments suivants installés sur votre système :

- Python 3.10, 3.11 ou 3.12 (3.12 recommandé) (utilisé dans build_scripts)
- Node/NPM (recommandé d'être installé avec NVM)
- PNPM
- Git

## Configuration de l'environnement de développement

### 1. Cloner le dépôt

```bash
git clone https://github.com/CybercentreCanada/clue.git
cd clue/ui
```

### 2. Installer Node/NPM avec NVM

Si vous n'avez pas NPM installé, suivez le
[guide d'installation officiel](https://github.com/nvm-sh/nvm?tab=readme-ov-file#installing-and-updating).

Vérifier l'installation de NPM :

```bash
npm --version
```

### 3. Installer PNPM avec NPM

Ce projet utilise PNPM pour gérer les dépendances, car il est plus rapide que le NPM par défaut (et les réseaux proxy
d'entreprise peuvent être assez lents).

PNPM peut simplement être installé en utilisant NPM :
```bash
npm install -g pnpm
```

### 4. Installer les dépendances du projet avec PNPM

Maintenant que PNPM est installé, vous pouvez installer les dépendances du projet :

```bash
pnpm install
```

Cela installera toutes les dépendances dans le répertoire node_modules.

## Flux de travail de développement

### Démarrer le serveur de développement

Démarrer l'interface utilisateur Clue en mode développement :

```bash
pnpm dev
```

### Exécuter les tests

Exécuter les tests :

```bash
pnpm test
```

Vous pouvez également exécuter des tests avec une interface utilisateur de terminal plus jolie en utilisant cette
commande :

```bash
pnpm test-ui
```

### Scripts supplémentaires

Pour plus d'options de lancement, consultez la section "scripts" du fichier package.json.

## Dépannage



## Obtenir de l'aide

Vous pouvez contacter l'équipe de développement Clue sur le discord aurora CCCS : <https://discord.gg/GUAy9wErNu>
