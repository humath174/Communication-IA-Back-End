import imaplib
import email
from email.header import decode_header
import mysql.connector
from datetime import datetime
import time
import chardet
import re
from dotenv import load_dotenv

load_dotenv()


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


def get_email_server_config():
    """Récupère la configuration du serveur e-mail depuis la base de données."""
    try:
        conn = connect_to_database()
        if conn:
            print("Connexion réussie, création du curseur...")
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT imap_server, email_address, password FROM email_accounts LIMIT 1")
            print("Requête exécutée, récupération des résultats...")
            result = cursor.fetchone()
            print(f"Résultat de la requête : {result}")
            cursor.close()
            conn.close()
            print("Connexion fermée.")

            if result:
                return result['imap_server'], result['email_address'], result['password']
            else:
                print("Aucune configuration d'e-mail trouvée dans la base de données.")
                return None, None, None
    except mysql.connector.Error as err:
        print(f"Erreur lors de la récupération de la configuration e-mail : {err}")
        return None, None, None


def insert_email_into_db(conn, to, sender, subject, message, timestamp):
    """Insertion d'un e-mail dans la table bdd_insertion."""
    cursor = conn.cursor()
    try:
        query = """
        INSERT INTO bdd_insertion (`to`, `from`, `subject`, `message`, `timestamp`)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (to, sender, subject, message, timestamp))
        conn.commit()
        print(f"je suis passé Insetion BDD")
    except mysql.connector.Error as err:
        print(f"Erreur lors de l'insertion des données : {err}")
    finally:
        cursor.close()


def decode_email_header(header_value):
    """Décode un en-tête d'e-mail."""
    decoded_parts = decode_header(header_value)
    decoded_string = ''
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            if encoding:
                decoded_string += part.decode(encoding)
            else:
                decoded_string += part.decode('utf-8', errors='replace')
        else:
            decoded_string += part
    return decoded_string


def decode_email_body(payload):
    """Décode le contenu principal de l'e-mail avec gestion automatique des encodages."""
    try:
        detected = chardet.detect(payload)  # Détecter automatiquement l'encodage
        encoding = detected.get('encoding', 'utf-8')
        return payload.decode(encoding, errors="replace")
    except Exception as e:
        print(f"Erreur lors du décodage du contenu : {e}")
        return payload.decode("latin1", errors="replace")


def clean_text(text):
    """Nettoyer le texte des sujets et expéditeurs."""
    if isinstance(text, bytes):
        return text.decode("utf-8", errors="ignore")
    return text


def extract_email(address):
    """Extrait uniquement l'adresse e-mail d'une chaîne contenant un nom et une adresse."""
    match = re.search(r"<(.+?)>", address)
    if match:
        return match.group(1)
    else:
        # Si l'adresse n'est pas encadrée par < >, on retourne la chaîne telle quelle
        return address


def fetch_emails():
    """Récupère les e-mails non lus et les insère dans la base de données."""
    try:
        # Récupérer la configuration du serveur e-mail depuis la base de données
        imap_server, email_address, password = get_email_server_config()
        if not imap_server or not email_address or not password:
            print("Impossible de récupérer la configuration du serveur e-mail.")
            return

        # Connexion au serveur IMAP
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_address, password)
        mail.select("inbox")

        # Recherche des e-mails non lus
        status, messages = mail.search(None, "UNSEEN")
        if status != "OK":
            print("Impossible de récupérer les e-mails.")
            return

        email_ids = messages[0].split()

        # Connexion à la base de données
        conn = connect_to_database()
        if not conn:
            return

        for email_id in email_ids:
            try:
                # Récupérer l'e-mail brut
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                if status != "OK":
                    print(f"Impossible de récupérer l'e-mail {email_id}.")
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        # Parse l'e-mail
                        msg = email.message_from_bytes(response_part[1])

                        # Décode les champs principaux
                        raw_sender = decode_email_header(msg["From"])
                        raw_to = decode_email_header(msg["To"])
                        subject = clean_text(decode_email_header(msg["Subject"]))
                        date = msg["Date"]

                        # Extraire uniquement l'adresse e-mail
                        sender = extract_email(raw_sender)
                        to = extract_email(raw_to)

                        # Convertir la date en format datetime
                        timestamp = datetime.strptime(date, "%a, %d %b %Y %H:%M:%S %z").strftime("%Y-%m-%d %H:%M:%S")

                        # Décoder le contenu du message
                        message = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                if content_type == "text/plain":  # On récupère uniquement le texte brut
                                    payload = part.get_payload(decode=True)
                                    if payload:
                                        message = decode_email_body(payload)
                                        break
                        else:
                            payload = msg.get_payload(decode=True)
                            if payload:
                                message = decode_email_body(payload)

                        # Insérer l'e-mail dans la base de données
                        insert_email_into_db(conn, to, sender, subject, message, timestamp)
            except Exception as e:
                print(f"Erreur lors du traitement de l'e-mail {email_id} : {e}")

        # Déconnexion
        conn.close()
        mail.logout()
    except Exception as e:
        print(f"Erreur lors de la récupération des e-mails : {e}")


if __name__ == "__main__":
    while True:
        fetch_emails()
        time.sleep(5)  # Attendre 1 minute avant de vérifier à nouveau