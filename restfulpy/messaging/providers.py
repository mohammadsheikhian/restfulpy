import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from os.path import basename

from mako.lookup import TemplateLookup
from nanohttp import settings, LazyAttribute
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from restfulpy.helpers import construct_class_by_name


class Messenger(object):
    """
    The abstract base class for everyone messaging operations
    """

    def render_body(self, body, template_filename=None):
        if template_filename:
            mako_template = self.lookup.get_template(template_filename)
            assert mako_template is not None, \
                'Cannot find template file: {template_filename}.'
            return mako_template.render(**body)

        return body

    @LazyAttribute
    def lookup(self):
        return TemplateLookup(
            module_directory=settings.messaging.mako_modules_directory,
            directories=settings.messaging.template_dirs,
            input_encoding='utf8'
        )

    def send(self, to, subject, body, cc=None, bcc=None,
             template_filename=None, from_=None, attachments=None):
        raise NotImplementedError


class SMTPProvider(Messenger):

    def send(self, to, subject, body, cc=None, bcc=None,
             template_filename=None, from_=None, attachments=None):
        """
        Sending messages with SMTP server
        """

        body = self.render_body(body, template_filename)

        smtp_config = settings.smtp
        smtp_server = (smtplib.SMTP_SSL if smtp_config.ssl else smtplib.SMTP)(
            host=smtp_config.host,
            port=smtp_config.port,
            local_hostname=smtp_config.local_hostname
        )
        if smtp_config.tls:  # pragma: no cover
            smtp_server.starttls()

        if smtp_config.auth:  # pragma: no cover
            smtp_server.login(smtp_config.username, smtp_config.password)

        from_ = from_ or smtp_config.username

        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = formataddr((from_, settings.smtp.username))
        msg['To'] = to
        if cc:
            msg['Cc'] = cc
        if bcc:
            msg['Bcc'] = bcc

        html_part = MIMEText(body, 'html')
        msg.attach(html_part)
        if attachments:
            for attachment in attachments:
                assert hasattr(attachment, 'name')
                attachment_part = MIMEApplication(
                    attachment.read(),
                    Name=basename(attachment.name)
                )
                attachment_part['Content-Disposition'] = \
                    f'attachment; filename="{basename(attachment.name)}"'
                msg.attach(attachment_part)

        smtp_server.send_message(msg)
        smtp_server.quit()


class SendGridProvider(Messenger):

    def send(self, to, subject, body, cc=None, bcc=None,
             template_filename=None, from_=None, attachments=None):
        """
        Sending messages with sendgrid
        The sender's email (default sender) in the configuration file
        should be a verified email
        """

        body = self.render_body(body, template_filename)
        message = Mail(
            from_email=(settings.smtp.username, from_),
            to_emails=to,
            subject=subject,
            html_content=body,
        )
        sendgrid = SendGridAPIClient(settings.messaging.api_key)
        sendgrid.send(message)


class ConsoleMessenger(Messenger):
    def send(self, to, subject, body, cc=None, bcc=None,
             template_filename=None, from_=None, attachments=None):
        """
        Sending messages by email
        """

        body = self.render_body(body, template_filename)
        print(body)


def create_messenger() -> Messenger:
    return construct_class_by_name(settings.messaging.default_messenger)
