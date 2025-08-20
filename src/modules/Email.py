import os.path
import smtplib
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

class EmailSender:
    def __init__(self, DashboardConfig):
        self.smtp = None
        self.DashboardConfig = DashboardConfig
        if not os.path.exists('./attachments'):
            os.mkdir('./attachments')
        
    def Server(self):
        return self.DashboardConfig.GetConfig("Email", "server")[1]
    
    def Port(self):
        return self.DashboardConfig.GetConfig("Email", "port")[1]
    
    def Encryption(self):
        return self.DashboardConfig.GetConfig("Email", "encryption")[1]
    
    def Username(self):
        return self.DashboardConfig.GetConfig("Email", "username")[1]
    
    def Password(self):
        return self.DashboardConfig.GetConfig("Email", "email_password")[1]
    
    def SendFrom(self):
        return self.DashboardConfig.GetConfig("Email", "send_from")[1]

    def ready(self):
        return all([self.Server(), self.Port(), self.Encryption(), self.Username(), self.Password(), self.SendFrom()])

    def send(self, receiver, subject, body, includeAttachment = False, attachmentName = ""):
        if self.ready():
            try:
                self.smtp = smtplib.SMTP(self.Server(), port=int(self.Port()))
                self.smtp.ehlo()
                if self.Encryption() == "STARTTLS":
                    self.smtp.starttls()
                self.smtp.login(self.Username(), self.Password())
                message = MIMEMultipart()
                message['Subject'] = subject
                message['From'] = self.SendFrom()
                message["To"] = receiver
                message.attach(MIMEText(body, "plain"))

                if includeAttachment and len(attachmentName) > 0:
                    attachmentPath = os.path.join('./attachments', attachmentName)
                    if os.path.exists(attachmentPath):
                        attachment = MIMEBase("application", "octet-stream")
                        with open(os.path.join('./attachments', attachmentName), 'rb') as f:
                            attachment.set_payload(f.read())
                        encoders.encode_base64(attachment)
                        attachment.add_header("Content-Disposition", f"attachment; filename= {attachmentName}",)
                        message.attach(attachment)
                    else:
                        self.smtp.close()
                        return False, "Attachment does not exist"
                self.smtp.sendmail(self.SendFrom(), receiver, message.as_string())
                self.smtp.close()
                return True, None
            except Exception as e:
                return False, f"Send failed | Reason: {e}"
        return False, "SMTP not configured"