import subprocess
import time

# Démarrer le script de récupération des emails
recuperation_process = subprocess.Popen(["python3", "recuperationmail.py"])

# Démarrer le script d'envoi des emails
envoi_process = subprocess.Popen(["python3", "envoiemail.py"])

# Démarrer le script d'envoi des emails
jugement_process = subprocess.Popen(["python3", "jugementmail.py"])

# Démarrer le script d'envoi des emails
reponse_process = subprocess.Popen(["python3", "reponsemail.py"])

try:
    while True:
        # Vérifie si un processus s'est arrêté
        if recuperation_process.poll() is not None:
            print("Le script recuperationmail.py s'est arrêté. Redémarrage...")
            recuperation_process = subprocess.Popen(["python3", "recuperationmail.py"])

        if envoi_process.poll() is not None:
            print("Le script envoiemail.py s'est arrêté. Redémarrage...")
            envoi_process = subprocess.Popen(["python3", "envoiemail.py"])

        if jugement_process.poll() is not None:
            print("Le script jugementmail.py s'est arrêté. Redémarrage...")
            jugement_process = subprocess.Popen(["python3", "envoiemail.py"])

        if reponse_process.poll() is not None:
            print("Le script reponsemail.py s'est arrêté. Redémarrage...")
            reponse_process = subprocess.Popen(["python3", "envoiemail.py"])

        time.sleep(10)  # Vérification toutes les 10 secondes

except KeyboardInterrupt:
    print("Arrêt des scripts...")
    recuperation_process.terminate()
    envoi_process.terminate()
