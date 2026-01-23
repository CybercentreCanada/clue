# Clue du point de vue du développeur de plugins

Pour que Clue puisse enrichir les données d'un outil, un plugin doit être développé pour servir d'interface avec l'outil
en question. Le serveur API central de Clue est un simple serveur Flask qui s'exécute généralement dans un pod sur un
cluster, et les plugins sont des serveurs séparés qui s'exécutent généralement dans des pods dans le même espace de
noms, et la communication entre les deux repose sur le réseau interne du cluster, bien que les plugins puissent être
hébergés n'importe où tant qu'ils sont accessibles par le serveur central.

## Démarrage

Chaque plugin est enregistré sur le serveur central par configuration, donc tout ce qui est nécessaire pour connecter
un plugin au serveur central est le nom du plugin, les types pris en charge par le plugin et où il peut être trouvé
(url/port).

La bibliothèque Python clue-api contient tout ce dont vous avez besoin pour commencer le développement de plugins, et
il existe également un référentiel de plugins modèle qui peut être utilisé pour démarrer rapidement le développement.
