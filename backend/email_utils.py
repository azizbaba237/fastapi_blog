from email.message import EmailMessage
import aiosmtplib
from fastapi.templating import Jinja2Templates
from config import settings

templates = Jinja2Templates(directory="templates")

async def send_email(
    to_email: str,
    subject: str,
    plain_text: str, 
    html_content: str | None = None
) -> None:
    """
    Send an email using the specified parameters.

    Args:
        to_email (str): The recipient's email address.
        subject (str): The subject of the email.
        plain_text (str): The plain text content of the email.
        html_content (str | None): Optional HTML content for the email.

    Raises:
        aiosmtplib.SMTPException: If there is an error sending the email.
    """
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(plain_text)

    if html_content:
        message.add_alternative(html_content, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.mail_server,
        port=settings.mail_port,
        username=settings.mail_username if settings.mail_username else None,
        password=settings.mail_password.get_secret_value() or None,
        start_tls=settings.mail_use_tls,
    )
    

async def send_password_reset_email(to_email: str, username: str, token: str) -> None:
    """
    Send a password reset email to the specified recipient.

    Args:
        to_email (str): The recipient's email address.
        token (str): The password reset token to include in the email.

    Raises:
        aiosmtplib.SMTPException: If there is an error sending the email.
    """
    reset_url = f"{settings.frontend_url}/reset-password?token={token}"
    
    template = templates.env.get_template("email/password_reset.html")
    html_content = template.render(reset_url=reset_url, username=username)
    
    plain_text = f"""Hi {username}
    
    Your request to reset your password has been received. Please click the link below to reset your password:

    {reset_url}

    This link will expire un 1 hour. 

    If you did not request a password reset, please ignore this email.

    Best regards, 
    The FastAPI Blog Team """
    
    await send_email(
        to_email=to_email,
        subject="Reset your Password - FastAPI Blog",
        plain_text=plain_text,
        html_content=html_content
    )
    