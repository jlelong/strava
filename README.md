# strava
Interface de consultation des activités Strava.
Nécessite stravalib, pymysql et un serveur mysql

1. Créer une base de données et deux tables

    * une table pour stocker les vélos au format

    id (VARCHAR(45)) l'id défini par Strava, c'est une string
    name (VARCHAR) non du vélo
    type (ENUM('road','mtb','cx','tt','any') type de sortie
    frame_type (INT) code Strava associée au type de sortie

    * une table pour stocker les sorties et toutes les informations
      associées

2. Créer un fichier setup.ini au format

```
[mysql]
base = "nom de la base de données"
bikes_table = "nom de la table contenant les différents vélos"
activities_table = "nom de la table contenant les activités"
user = 
password = 

[strava]
token = "token Strava à récupérer dans Mon Compte/Mes Applis"
```
