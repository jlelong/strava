# StravaView

Interface de consultation des activités vélo et course de Strava. Cette interface
est une application Web client/serveur nécessitant

- un serveur MySQL
- Voir le fichier `requirements.txt`

## Installation

1. Créer une base de données et lui associer un utilisateur

    La création des tables est faite directement par le code Python

1. Créer un fichier setup.ini

    Copier le fichier `setup.ini.dist` sous le nom `setup.ini` et le compléter avec les informations d'authentification associées

    * à la base de données locale
        * `base` : le nom de la base
        * `user` : un utilisateur MySQL ayant à la base déclarée au dessus
        * `password` : le mot de passe de l'utilisateur `user`, peut être vide
    * Strava
        * `client_id`
        * `client_secret`

        Ces informations ne sont disponibles qu'après avoir déclaré une application à labs.strava.com/developers.

    * server
        * `session_dir`: where yo save the session information
        * `athlete_whitelist`: list of authorized athletes. One id per line
        * `base_proxy`: url for `tools.proxy.base` config of `cherrypy`

## Application Web

Lancer

``
python ./run.py
``

et pointer un navigateur vers `http://localhost:8080`.
