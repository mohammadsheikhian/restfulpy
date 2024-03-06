import requests
import ujson
from kavenegar import KavenegarAPI
from nanohttp import settings
from twilio.rest import Client

from restfulpy.helpers import construct_class_by_name


class SmsProvider:

    def __init__(self, config):
        self.config = config

    def send(self, to_number, text, *args, **kwargs):
        raise NotImplementedError()

    @property
    def name(self):
        raise NotImplementedError()

class CmSmsProvider(SmsProvider):

    @property
    def name(self):
        return 'Cm'

    def send(self, to_number, text, *args, **kwargs):
        headers = {'Content-Type': 'application/json'}
        data = {
            "messages": {
                "authentication": {"productToken": self.config.api_key},
                "msg": [{
                    "body": {"content": text},
                    "from": self.config.sender,
                    "to": [{"number": f'{to_number}'}],
                    "reference": self.config.reference
                }]
            }
        }
        data = ujson.dumps(data)

        requests.post(
            self.config.url,
            data=data,
            headers=headers
        )


class IranKavenegarSmsProvider(SmsProvider):

    @property
    def name(self):
        return 'kavenegar'

    def send(self, to_number, text, *args, **kwargs):
        api = KavenegarAPI(self.config.api_key)
        params = {
            'sender': '',  # optional
            'receptor': str(to_number),
            'message': text,
        }
        api.sms_send(params)


class ConsoleSmsProvider(SmsProvider):

    @property
    def name(self):
        return 'console'

    def send(self, to_number, text, *args, **kwargs):
        print(
            'SMS send request received for number : %s with text : %s' %
            (to_number, text)
        )


class TwilioSmsProvider(SmsProvider):

    @property
    def name(self):
        return 'twilio'

    def send(self, to_number, text, *args, **kwargs):
        client = Client(self.config.api_key[0], self.config.api_key[1])
        channel = self.config.channel
        if channel is None:
            channel = 'sms'

        message = client.messages.create(
            from_=f'{channel}:+{self.config.sender}',
            to=f'{channel}:+{to_number}',
            **kwargs,
        )


def create_sms_provider(to_number):
    for key, value in settings.sms.providers.items():
        if str(to_number).startswith(str(key)):
            return construct_class_by_name(value.name, config=value)
    return construct_class_by_name(
        settings.sms.default_provider.name, settings.sms.default_provider
    )

