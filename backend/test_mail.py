import asyncio
import aiosmtplib
from email.message import EmailMessage
from config import settings

async def test_smtp():
    msg = EmailMessage()
    msg["From"] = settings.mail_from
    msg["To"] = "test@example.com"
    msg["Subject"] = "Test Mailtrap Direct"
    msg.set_content("Connexion reussie.")

    pwd = settings.mail_password.get_secret_value() if hasattr(settings.mail_password, "get_secret_value") else settings.mail_password

    print("Connexion au serveur Mailtrap...")
    res = await aiosmtplib.send(
        msg,
        hostname=settings.mail_server,
        port=settings.mail_port,
        username=settings.mail_username,
        password=pwd,
        start_tls=settings.mail_use_tls
    )
    print("Résultat de l'envoi :", res)

asyncio.run(test_smtp())