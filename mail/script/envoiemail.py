import mysql.connector
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# Configuration de la base de données MySQL
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME")
}


# Fonction pour envoyer un email
def send_email(to, subject, body, from_email):
    try:
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to
        msg['Subject'] = subject

        # Attacher le message
        msg.attach(MIMEText(body, 'plain'))

        # Connexion au serveur SMTP (ici, un exemple avec un serveur SMTP fictif)
        server = smtplib.SMTP('smtp.mailo.com', 587)
        server.starttls()
        server.login(from_email, "AIprojectvoix")  # Remplacez par le mot de passe réel
        server.sendmail(from_email, to, msg.as_string())
        server.quit()

        return True
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email: {e}")
        return False


# Connexion à la base de données
try:
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()
except mysql.connector.Error as err:
    print(f"Erreur de connexion: {err}")
    exit()

# Récupérer les e-mails avec sent = 1
cursor.execute("""
    SELECT id, email_to, email_from, subject, original_message, reply_message, action_timestamp
    FROM responses 
    WHERE sent = 1
""")
emails_to_send = cursor.fetchall()

# Processus d'envoi et mise à jour des tables
for email in emails_to_send:
    email_id, email_to, email_from, subject, original_message, reply_message, action_timestamp = email

    # Envoi de l'e-mail
    if send_email(email_to, "Re: " + subject, reply_message, email_from):
        print(f"Email envoyé à {email_to} avec succès.")

        # Suppression de la ligne après l'envoi
        cursor.execute("DELETE FROM responses WHERE id = %s", (email_id,))

        # Ajouter l'entrée dans la nouvelle base de données (table d'historique ou similaire)
        cursor.execute("""
            INSERT INTO email_history (email_id, email_to, email_from, subject, original_message, reply_message, action_timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (email_id, email_to, email_from, subject, original_message, reply_message, action_timestamp))

        # Confirmer les changements
        connection.commit()

# Fermer la connexion à la base de données
cursor.close()
connection.close()
