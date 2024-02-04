from unittest.mock import patch

import ujson
from nanohttp import settings, configure

from restfulpy.messaging.sms import CmSmsProvider, IranSmsProvider, \
    ConsoleSmsProvider, AutomaticSmsProvider


def test_cm_cms_provider():
    configure(force=True)
    settings.merge(
        f'''
        sms:
          provider:
            worldwide: restfulpy.messaging.sms.ConsoleSmsProvider
            iran: restfulpy.messaging.sms.ConsoleSmsProvider
          sender: cas@Omadeus
          reference: Omadeus
          token: <token>
          url: https://gw.cmtelecom.com/v1.0/message
        ''',
    )
    with patch('requests.post') as mock_post:
        provider = CmSmsProvider()
        provider.send('1234567890', 'Hello, World!')
        mock_post.assert_called_once_with(
            settings.sms.url,
            data=ujson.dumps({
                'messages': {
                    'authentication': {'productToken': settings.sms.token},
                    'msg': [{
                        'body': {'content': 'Hello, World!'},
                        'from': settings.sms.sender,
                        'to': [{'number': '1234567890'}],
                        'reference': settings.sms.reference
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
          provider:
            worldwide: restfulpy.messaging.sms.ConsoleSmsProvider
            iran: restfulpy.messaging.sms.ConsoleSmsProvider
          sender: cas@Omadeus
          reference: Omadeus
          token: <token>
          url: https://gw.cmtelecom.com/v1.0/message
        ''',
    )
    with patch('kavenegar.KavenegarAPI.sms_send') as mock_post:
        provider = IranSmsProvider()
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
          provider:
            worldwide: restfulpy.messaging.sms.ConsoleSmsProvider
            iran: restfulpy.messaging.sms.ConsoleSmsProvider
          sender: cas@Omadeus
          reference: Omadeus
          token: <token>
          url: https://gw.cmtelecom.com/v1.0/message
        ''',
    )
    with patch('builtins.print') as mock_post:
        provider = ConsoleSmsProvider()
        provider.send('1234567890', 'Hello, World!')
        mock_post.assert_called_once_with(
            'SMS send request received for number : 1234567890 with text : Hello, World!',
        )


def test_auto_sms_provider():
    configure(force=True)
    settings.merge(
        f'''
        sms:
          provider:
            worldwide: restfulpy.messaging.sms.ConsoleSmsProvider
            iran: restfulpy.messaging.sms.ConsoleSmsProvider
          sender: cas@Omadeus
          reference: Omadeus
          token: <token>
          url: https://gw.cmtelecom.com/v1.0/message
        ''',
    )
    provider = AutomaticSmsProvider()
    assert isinstance(provider.iran_sms_provider, ConsoleSmsProvider)
    assert isinstance(provider.worldwide_sms_provider, ConsoleSmsProvider)

    settings.merge('''
    sms:
      provider:
        worldwide: restfulpy.messaging.sms.CmSmsProvider
        iran: restfulpy.messaging.sms.IranSmsProvider
    ''')

    provider = AutomaticSmsProvider()
    assert isinstance(provider.iran_sms_provider, IranSmsProvider)
    assert isinstance(provider.worldwide_sms_provider, CmSmsProvider)

