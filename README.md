# StravaView
Interface de consultation des activités vélo de Strava. Cette interface
contient deux parties : 
* une base de données et des fonctionnalités Python associées.  
    Nécessite un serveur mysql et les modules Python ``geopy``, ``pymysql`` et ``stravalib``.
* une application web de consultation de la base de données.  
    Nécessite le module Python ``cherrypy`` qui permet de faire tourner un
    serveur Web.


## Base de données et accès Python

1. Créer une base de données et lui associer un utilisateur

    La création des tables est faites directement par le code Python

1. Créer un fichier setup.ini

    Copier le fichier ``setup.ini.dist`` sous le nom ``setup.ini`` et
    le compléter avec les informations d'authentification associées à la
    base de données locale et à Strava.


1. Utiliser l'interface Python

    Connection
    ```
    from readconfig import read_config
    from stravaview.stravadb import Strava

    config = read_config('setup.ini')
    strava_instance = Strava(config)
    ```
    
    Création des tables
    ```
    strava_instance.create_bikes_table()
    strava_instance.create_activities_table()
    ```

    Mise à jour des tables locales
    ```
    strava_instance.update_bikes()
    strava_instance.update_activities()
    ```

    Fermeture de la connection
    ```
    strava_instance.close()
    ```

1. Requêter la table des activités

    La fonction suivante permet d'effectuer dans la table des activités en
    spécifiant une plage de dates pour l'activité et une sous-chaîne du nom
    de l'activité.

    ```
    stravaview.stravadb.get_activities(before=None, after=None, name=None, 
                                       bikeype=None, json_output=False)
    ```

    Les dates `before` et `after` peuvent être spécifiées comme des chaînes
    de caractères sous la forme `'YYY-MM-DD'` ou comme des dates
    `datetime.date(YYY, MM, DD)` ou même `datetime.datetime`.

    L'argument ``json_output`` permet de spécifier que la fonction renvoie
    une réponse au format JSON.

    Example 

    ```
    from readconfig import read_config
    from stravaview.stravadb import Strava

    config = read_config('setup.ini')
    strava_instance = Strava(config)
    strava_instance.get_activities(after='2016-12-01', name='Pellet', biketype='mtb')
    strava_instance.close()
    ```

## Application Web

Cette partie nécessite la partie précédente.
Cette application Web est une interface de consultation de la base
précédente et utilise les fonctionnalités Python précédentes.

Lancer
```
python ./wui/server/serve.py
```
et pointer un navigateur vers `http://localhost:8080`.
    
