# strava
Interface de consultation des activités vélo de Strava.
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

3. Première utilisation
    ```
    from readconfig import read_config
    from stravaview.stravadb import Strava

    config = read_config('setup.ini')
    strava_instance = Strava(config)
    strava_instance.create_bikes_table()
    strava_instance.create_activities_table()
    ```

4. Mise à jour des tables locales

    ```
    from readconfig import read_config
    from stravaview.stravadb import Strava

    config = read_config('setup.ini')
    strava_instance = Strava(config)
    strava_instance.update_bikes()
    strava_instance.update_activities()
    ```
