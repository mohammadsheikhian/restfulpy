from unittest.mock import patch

import ujson
from nanohttp import settings, configure

from restfulpy.messaging.sms import create_sms_provider, ConsoleSmsProvider, \
    CmSmsProvider, IranKavenegarSmsProvider, TwilioSmsProvider


def test_sms_provider():
    configure(force=True)
    settings.merge(
        f'''
        sms:
          default_provider:
            name: restfulpy.messaging.sms.ConsoleSmsProvider
            api_key: <API-key>
            url: <url>
            sender: <sender>
            reference: <reference>
            channel: console
          
          providers:
            98:
              name: restfulpy.messaging.sms.IranKavenegarSmsProvider
              api_key: 123456abcd
              url: <url>
              sender: <sender>
              reference: <reference>
              channel: sms
            1:
              name: restfulpy.messaging.sms.TwilioSmsProvider
              api_key: [abcd, a123b]
              url: <url>
              sender: 123456
              reference: <reference>
              channel: whatsapp
        ''',
    )
    provider = create_sms_provider(2011111)
    assert isinstance(provider, ConsoleSmsProvider) is True
    assert provider.config.channel == 'console'

    provider = create_sms_provider(9811111)
    assert isinstance(provider, IranKavenegarSmsProvider) is True
    assert provider.config.channel == 'sms'

    provider = create_sms_provider(111111)
    assert isinstance(provider, TwilioSmsProvider) is True
    assert provider.config.channel == 'whatsapp'
    assert provider.config.api_key == ['abcd', 'a123b']


def test_twilio_provider():
    configure(force=True)
    settings.merge(
        f'''
        sms:
          default_provider:
            name: restfulpy.messaging.sms.TwilioSmsProvider
            api_key: [abcd, a123b]
            url: <url>
            sender: 123456
            reference: <reference>
            channel: whatsapp
        ''',
    )

    with patch('restfulpy.messaging.sms.TwilioSmsProvider.send') as mock_post:
        kwargs = dict(
            messaging_service_sid='MG',
            content_variables=ujson.dumps({'1': 'https://s.xeba.tech/abc12'}),
            content_sid='HX',
        )
        provider = TwilioSmsProvider(settings.sms.default_provider)
        provider.send(to_number='1123456', text='', **kwargs)
        mock_post.assert_called_once_with(
            to_number='1123456',
            text='',
            messaging_service_sid='MG',
            content_variables=ujson.dumps({'1': 'https://s.xeba.tech/abc12'}),
            content_sid='HX',
        )


def test_cm_cms_provider():
    configure(force=True)
    settings.merge(
        f'''
        sms:
          default_provider:
            name: restfulpy.messaging.sms.ConsoleSmsProvider
            sender: cas@Omadeus
            reference: Omadeus
            api_key: <token>
            url: https://gw.cmtelecom.com/v1.0/message
        ''',
    )

    with patch('requests.post') as mock_post:
        provider = CmSmsProvider(settings.sms.default_provider)
        provider.send('1234567890', 'Hello, World!')
        mock_post.assert_called_once_with(
            settings.sms.default_provider.url,
            data=ujson.dumps({
                'messages': {
                    'authentication': {
                        'productToken': settings.sms.default_provider.api_key
                    },
                    'msg': [{
                        'body': {'content': 'Hello, World!'},
                        'from': settings.sms.default_provider.sender,
                        'to': [{'number': '1234567890'}],
                        'reference': settings.sms.default_provider.reference
                    }]
                }
            }),
            headers={'Content-Type': 'application/json'}
        )


def test_iran_sms_provider():
    configure(force=True)
    settings.merge(
        f'''
        sms:
          default_provider:
            name: restfulpy.messaging.sms.IranKavenegarSmsProvider
            sender: cas@Omadeus
            reference: Omadeus
            api_key: <token>
            url: https://gw.cmtelecom.com/v1.0/message
        ''',
    )
    with patch('kavenegar.KavenegarAPI.sms_send') as mock_post:
        provider = IranKavenegarSmsProvider(settings.sms.default_provider)
        provider.send('1234567890', 'Hello, World!')
        mock_post.assert_called_once_with(
            {
                'sender': '',
                'receptor': str('1234567890'),
                'message': 'Hello, World!',
            },
        )


def test_console_sms_provider():
    configure(force=True)
    settings.merge(
        f'''
        sms:
          default_provider:
            name: restfulpy.messaging.sms.ConsoleSmsProvider
            sender: cas@Omadeus
            reference: Omadeus
            api_key: <token>
            url: https://gw.cmtelecom.com/v1.0/message
        ''',
    )
    with patch('builtins.print') as mock_post:
        provider = ConsoleSmsProvider(settings.sms.default_provider)
        provider.send('1234567890', 'Hello, World!')
        mock_post.assert_called_once_with(
            'SMS send request received for number : '
            '1234567890 with text : Hello, World!',
        )

