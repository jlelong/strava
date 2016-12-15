# strava
Interface de consultation des activités Strava.
Nécessite stravalib, pymysql et un serveur mysql

1. Créer un fichier setup.ini au format

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

2. Créer une base de données de nom défini par ``base`` ayant pour
   utilisateur ``user``

    La création des tables est faites directement par le code Python

