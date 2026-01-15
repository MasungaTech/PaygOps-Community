import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.utils import COMMASPACE, formatdate
from email import encoders


class EmailSender:

    SENDER_EMAIL = os.getenv('SENDER_EMAIL', 'donotreply@paygopsapp.com')
    EMAIL_SERVER_URL = 'smtp.sendgrid.net'
    EMAIL_SERVER_USER = "apikey"
    EMAIL_SERVER_PASSWORD = os.getenv('EMAIL_SERVER_PASSWORD', '')

    HTML_EMAIL_TEMPLATE = "From: PaygOps Support Team <{email_from}>\n" \
                          "To: {name} <{email_to}>\n" \
                          "Subject: {subject}\n" \
                          "Content-type: text/html;charset=UTF-8\n" \
                          "\n{content}"

    BASIC_EMAIL_TEMPLATE = "From: PaygOps Support Team <{email_from}>\n" \
                           "To: {name} <{email_to}>\n" \
                           "Subject: {subject}\n" \
                           "\n{content}"

    def __init__(self, recipient_name, recipient, subject, body, html=False):
        self.recipient = recipient
        if not isinstance(self.recipient, list):
            self.recipient = [self.recipient]
        self.recipient_name = recipient_name
        self.subject = subject
        self.body = body
        self.html = html

    def send(self):
        text = (self.HTML_EMAIL_TEMPLATE if self.html else self.BASIC_EMAIL_TEMPLATE).format(
            name=self.recipient_name,
            email_from=self.SENDER_EMAIL,
            email_to=self.recipient,
            subject=self.subject,
            content=self.body
        )
        server = smtplib.SMTP_SSL(self.EMAIL_SERVER_URL, 465)
        server.ehlo()
        server.login(self.EMAIL_SERVER_USER, self.EMAIL_SERVER_PASSWORD)
        server.sendmail(self.SENDER_EMAIL, self.recipient, text.encode('utf-8'), mail_options=('SMTPUTF8'))
        server.close()

    def send_with_attachment(self, attachments=[]):
        msg = MIMEMultipart()
        msg['From'] = self.SENDER_EMAIL
        msg['To'] = COMMASPACE.join(self.recipient)
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = self.subject
        msg.attach(MIMEText(self.body))
        for attachment, attachment_name in attachments:
            part = MIMEText(attachment)
            part.add_header('Content-Disposition', 'attachment', filename=attachment_name) 
            msg.attach(part)
        server = smtplib.SMTP_SSL(self.EMAIL_SERVER_URL, 465)
        server.ehlo()
        server.login(self.EMAIL_SERVER_USER, self.EMAIL_SERVER_PASSWORD)
        server.sendmail(self.SENDER_EMAIL, self.recipient, msg.as_string())
        server.close()
        