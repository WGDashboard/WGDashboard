import os.path
import smtplib

# Email libaries
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

class EmailSender:
    def __init__(self, DashboardConfig):
        self.DashboardConfig = DashboardConfig

        if not os.path.exists('./attachments'):
            os.mkdir('./attachments')

        self.refresh_vals()

    def refresh_vals(self):
        self.Server = self.DashboardConfig.GetConfig("Email", "server")[1]
        self.Port = self.DashboardConfig.GetConfig("Email", "port")[1]

        self.Encryption = self.DashboardConfig.GetConfig("Email", "encryption")[1]
        self.AuthRequired = self.DashboardConfig.GetConfig("Email", "authentication_required")[1]
        self.Username = self.DashboardConfig.GetConfig("Email", "username")[1]
        self.Password = self.DashboardConfig.GetConfig("Email", "email_password")[1]

        self.SendFrom = self.DashboardConfig.GetConfig("Email", "send_from")[1]

    def is_ready(self) -> bool:
        self.refresh_vals()

        if self.AuthRequired:
            ready = all([
                self.Server, self.Port, self.Encryption,
                self.Username, self.Password, self.SendFrom
            ])
        else:
            ready = all([
                self.Server, self.Port, self.Encryption, self.SendFrom
            ])
        return ready

    def send(self, receiver, subject, body, includeAttachment: bool = False, attachmentName: str = "") -> tuple[bool, str | None]:
        if not self.is_ready():
            return False, "SMTP not configured"

        message = MIMEMultipart()
        message['Subject'] = subject
        message['From'] = self.SendFrom
        message["To"] = receiver
        message["Date"] = formatdate(localtime=True)
        message.attach(MIMEText(body, "plain"))

        if includeAttachment and len(attachmentName) > 0:
            attachmentPath = os.path.join('./attachments', attachmentName)

            if not os.path.exists(attachmentPath):
                return False, "Attachment does not exist"

            attachment = MIMEBase("application", "octet-stream")
            with open(os.path.join('./attachments', attachmentName), 'rb') as f:
                attachment.set_payload(f.read())

            encoders.encode_base64(attachment)
            attachment.add_header("Content-Disposition", f"attachment; filename= {attachmentName}",)
            message.attach(attachment)

        smtp = None
        try:
            smtp = smtplib.SMTP(self.Server, port=int(self.Port))
            smtp.ehlo()

            # Configure SMTP encryption type
            if self.Encryption == "STARTTLS":
                smtp.starttls()
                smtp.ehlo()

            # Log into the SMTP server if required
            if self.AuthRequired:
                smtp.login(self.Username, self.Password)

            # Send the actual email from the SMTP object
            smtp.sendmail(self.SendFrom, receiver, message.as_string())
            return True, None

        except Exception as e:
            return False, f"Send failed | Reason: {e}"

        finally:
            if smtp:
                smtp.quit()