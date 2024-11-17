import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "resourcemap001@gmail.com"
SMTP_PASSWORD = "puugvnyznfkukixt"


def send_email(recipient_email, subject, body):
    try:
        # Create the email
        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = recipient_email
        msg["Subject"] = subject

        # Attach the HTML body
        msg.attach(MIMEText(body, "html"))

        # Connect to the server
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)

        # Send the email
        server.sendmail(SMTP_USER, recipient_email, msg.as_string())

        # Disconnect from the server
        server.quit()

        return "Email sent successfully!"

    except Exception as e:
        return str(e)
