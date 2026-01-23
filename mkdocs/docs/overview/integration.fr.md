# Clue du point de vue de l'intégrateur

Cet outil est conçu pour être intégré dans d'autres outils de Centre des Opérations de Sécurité (SOC), afin d'enrichir
et d'interconnecter les différents outils utilisés et permettre aux analystes d'évaluer rapidement et de pivoter d'un
outil à l'autre.

Clue permet aux développeurs d'outils d'enrichir les indicateurs (tels que les IPs potentiellement malveillantes, les
 noms d'hôtes, les ports, etc.) en interrogeant dynamiquement ces indicateurs dans tous les autres outils pertinents et
 en affichant les résultats directement dans votre interface utilisateur.

Par exemple, si vous utilisiez d'autres outils open-source du CCCS tels que Howler (un outil de triage des alertes) et
Assemblyline (un outil d'analyse de logiciels malveillants). Avec l'intégration de Clue, lors de l'utilisation de
Howler, si vous regardiez une alerte contenant un indicateur de hachage de fichier, l'enrichissement de Clue
rechercherait automatiquement le hachage de fichier dans Assemblyline et vous indiquerait directement s'il est connu
dans Assemblyline, ainsi que des informations supplémentaires sur le hachage de fichier.

Cette section s'adresse aux développeurs d'outils qui souhaitent intégrer les enrichissements, actions ou récupérateurs
de Clue dans leur propre application.

### Intégration de Clue dans votre interface utilisateur

Afin d'enrichir les indicateurs dans votre interface utilisateur, vous devrez importer le package npm clue-ui dans
votre projet, initialiser le ClueProvider avec certaines valeurs de configuration telles que l'URL du serveur API Clue,
et simplement utiliser l'un des composants enrichis, ou l'un des hooks disponibles pour enrichir les données en question.

### Enrichissements

Comme mentionné précédemment, Clue fournit des composants et des hooks qui vous permettent simplement d'encapsuler vos
indicateurs et de les enrichir en interrogeant tous les plugins pertinents et en affichant les informations dans le composant.

### Actions

Clue permet également d'exécuter des actions prédéfinies sur n'importe quel indicateur. Chaque plugin fournira à Clue
une liste des actions disponibles, et la bibliothèque clue-ui fournit des fonctions qui vous permettent de lister ces
actions, ainsi que de les exécuter. Certaines actions peuvent également nécessiter la spécification de paramètres
supplémentaires, il existe donc également des composants fournis pour créer un formulaire afin de fournir ces
informations supplémentaires.

### Récupérateurs

Les récupérateurs sont une autre fonctionnalité qui permet aux développeurs de plugins de rendre les données de manière
plus détaillée, comme la génération d'un fichier markdown, de données JSON ou même d'une image. Cela pourrait être
utile pour générer des rapports détaillés sur un indicateur, rendre un fichier de messagerie et prendre une capture
d'écran, ou même afficher des graphiques.
