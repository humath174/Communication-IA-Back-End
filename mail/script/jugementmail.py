import openai
import mysql.connector
import time  # Pour ajouter le délai entre les vérifications
import os
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# Configuration de l'API OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configuration de la base de données
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}


def connect_to_database():
    """Connexion à la base de données."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Erreur de connexion à la base de données : {err}")
        return None


def classify_email_with_chatgpt(subject, message):
    """
    Utilise ChatGPT pour classifier l'e-mail comme nécessitant une réponse ou un transfert.
    """
    messages = [
        {"role": "system", "content": "You are an email assistant that classifies emails."},
        {"role": "user", "content": f"""
        Voici un e-mail :
        Sujet : {subject}
        Message : {message}

        Classifie cet e-mail en deux catégories : 
        - "reply" si une réponse est nécessaire. 
        - "transfer" si l'e-mail doit être transféré à un gestionnaire ou une assistance technique.

        Répond simplement par l'une des deux catégories : "reply" ou "transfer".
        """}
    ]
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Modèle GPT-3.5
            messages=messages,
            max_tokens=10,
            temperature=0
        )
        action = response.choices[0].message['content'].strip().lower()
        if action not in ["reply", "transfer"]:
            action = "reply"  # Par défaut
        return action
    except Exception as e:
        print(f"Erreur avec l'API OpenAI : {e}")
        return "reply"  # Par défaut


def process_emails():
    """
    Traite les e-mails depuis la base de données et décide de l'action.
    """
    conn = connect_to_database()
    if not conn:
        return

    cursor = conn.cursor(dictionary=True)

    try:
        # Récupérer les e-mails non encore classifiés
        cursor.execute("SELECT * FROM bdd_insertion WHERE id NOT IN (SELECT email_id FROM actions);")
        emails = cursor.fetchall()

        for email in emails:
            email_id = email["id"]
            to = email["to"]
            sender = email["from"]
            subject = email["subject"]
            message = email["message"]
            timestamp = email["timestamp"]

            # Classifier l'e-mail avec ChatGPT
            action = classify_email_with_chatgpt(subject, message)

            # Insérer dans la table correspondante
            if action == "reply":
                insert_reply(conn, email_id, to, sender, subject, message, timestamp)
            elif action == "transfer":
                insert_transfer(conn, email_id, to, sender, subject, message, timestamp)

            # Enregistrer l'action dans une table de log
            log_action(conn, email_id, action)

    except mysql.connector.Error as err:
        print(f"Erreur lors du traitement des e-mails : {err}")
    finally:
        cursor.close()
        conn.close()


def insert_reply(conn, email_id, to, sender, subject, message, timestamp):
    """Insère l'e-mail dans la table bdd_reponse."""
    cursor = conn.cursor()
    try:
        query = """
        INSERT INTO bdd_reponse (`to`, `from`, `subject`, `message`, `timestamp`, `timestamprepone`)
        VALUES (%s, %s, %s, %s, %s, NOW())
        """
        cursor.execute(query, (to, sender, subject, message, timestamp))

        # Suppression de l'entrée dans bdd_insertion
        query_delete = "DELETE FROM bdd_insertion WHERE id = %s"
        cursor.execute(query_delete, (email_id,))

        conn.commit()
    except mysql.connector.Error as err:
        print(f"Erreur lors de l'insertion dans bdd_reponse : {err}")
    finally:
        cursor.close()


def insert_transfer(conn, email_id, to, sender, subject, message, timestamp):
    """Insère l'e-mail dans la table bdd_transfert."""
    cursor = conn.cursor()
    try:
        query = """
        INSERT INTO bdd_transfert (`to`, `from`, `subject`, `message`, `timestamp`, `timestamptransfert`)
        VALUES (%s, %s, %s, %s, %s, NOW())
        """
        cursor.execute(query, (to, sender, subject, message, timestamp))

        # Suppression de l'entrée dans bdd_insertion
        query_delete = "DELETE FROM bdd_insertion WHERE id = %s"
        cursor.execute(query_delete, (email_id,))

        conn.commit()
    except mysql.connector.Error as err:
        print(f"Erreur lors de l'insertion dans bdd_transfert : {err}")
    finally:
        cursor.close()


def log_action(conn, email_id, action):
    """Log l'action effectuée dans une table de suivi."""
    cursor = conn.cursor()
    try:
        query = """
        INSERT INTO actions (email_id, action, action_timestamp)
        VALUES (%s, %s, NOW())
        """
        cursor.execute(query, (email_id, action))
        conn.commit()
    except mysql.connector.Error as err:
        print(f"Erreur lors de l'enregistrement de l'action : {err}")
    finally:
        cursor.close()


if __name__ == "__main__":
    while True:
        process_emails()
        time.sleep(1)  # Attendre 5 secondes avant de vérifier à nouveau
