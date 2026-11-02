#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import time


def attendre_base_de_donnees():
    """
    Au démarrage du serveur (ex. redémarrage de la machine), attend que MySQL accepte les connexions
    avant de lancer Django. Sans cela, Django plante si MySQL n'est pas encore prêt et le conteneur
    reste « vivant » sans servir l'application. Si la base reste injoignable, on sort en erreur
    pour que Docker relance le conteneur (restart: unless-stopped).
    """
    hote = os.environ.get('DB_HOST')
    if not hote:
        return
    delai = int(os.environ.get('DB_WAIT_TIMEOUT', '300'))
    debut = time.time()
    tentative = 0
    while True:
        try:
            import MySQLdb
            MySQLdb.connect(
                host=hote,
                port=int(os.environ.get('MYSQL_PORT', '3306')),
                user=os.environ.get('MYSQL_USER'),
                passwd=os.environ.get('MYSQL_PASSWORD'),
                db=os.environ.get('MYSQL_DATABASE'),
                connect_timeout=5,
            ).close()
            if tentative:
                print(f"Base de données prête après {int(time.time() - debut)} s.", flush=True)
            return
        except Exception as erreur:
            tentative += 1
            if time.time() - debut > delai:
                print(f"Base de données injoignable après {delai} s : {erreur}", flush=True)
                sys.exit(1)
            print(f"En attente de la base de données ({hote})… tentative {tentative} : {erreur}", flush=True)
            time.sleep(3)


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scolarite.settings')
    # Le processus parent du rechargement automatique attend la base ; l'enfant (RUN_MAIN) démarre ensuite.
    if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') != 'true':
        attendre_base_de_donnees()
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
