import requests
import ujson
from kavenegar import KavenegarAPI
from nanohttp import settings

from restfulpy.helpers import construct_class_by_name


class SmsProvider:  # pragma: no cover
    def send(self, to_number, text):
        raise NotImplementedError()


class CmSmsProvider(SmsProvider):  # pragma: no cover
    def send(self, to_number, text):
        headers = {'Content-Type': 'application/json'}
        data = {
            "messages": {
                "authentication": {"productToken": settings.sms.token},
                "msg": [{
                    "body": {"content": text},
                    "from": settings.sms.sender,
                    "to": [{"number": f'{to_number}'}],
                    "reference": settings.sms.reference
                }]
            }
        }
        data = ujson.dumps(data)

        requests.post(
            settings.sms.url,
            data=data,
            headers=headers
        )


class IranSmsProvider(SmsProvider):  # pragma: no cover
    def send(self, to_number, text):
        api = KavenegarAPI(settings.sms.token)
        params = {
            'sender': '',  # optional
            'receptor': str(to_number),
            'message': text,
        }
        api.sms_send(params)


class AutomaticSmsProvider(SmsProvider):  # pragma: no cover
    __worldwide_sms_provider = None
    __iran_sms_provider = None

    @property
    def worldwide_sms_provider(self):
        if not self.__worldwide_sms_provider:
            self.__worldwide_sms_provider = \
                construct_class_by_name(settings.sms.provider.worldwide)
        return self.__worldwide_sms_provider

    @property
    def iran_sms_provider(self):
        if not self.__iran_sms_provider:
            self.__iran_sms_provider = \
                construct_class_by_name(settings.sms.provider.iran)
        return self.__iran_sms_provider

    def send(self, to_number, text):
        if str(to_number).startswith('98'):
            self.iran_sms_provider.send(to_number=to_number, text=text)
        else:
            self.worldwide_sms_provider.send(to_number=to_number, text=text)


class ConsoleSmsProvider(SmsProvider):  # pragma: no cover
    def send(self, to_number, text):
        print(
            'SMS send request received for number : %s with text : %s' %
            (to_number, text)
        )

