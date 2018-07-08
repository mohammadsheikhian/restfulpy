import unittest

from nanohttp import settings

from restfulpy.orm import DBSession, Field, FakeJson
from restfulpy.messaging import BaseEmail, create_messenger
from restfulpy.tests.helpers import WebAppTestCase
from restfulpy.testing import MockupApplication


class Welcome(BaseEmail):
    __tablename__ = 'welcome'

    __mapper_args__ = {
        'polymorphic_identity': 'welcome'
    }

    body = Field(FakeJson, json='body')

    @property
    def email_body(self):
        return self.body

    @property
    def template_filename(self):
        return None


class MessagingModelTestCase(WebAppTestCase):
    application = MockupApplication('MockupApplication', None)
    __configuration__ = '''
    db:
      url: sqlite://    # In memory DB
      echo: false

    messaging:
      default_sender: test@example.com
      default_messenger: restfulpy.testing.MockupMessenger
    '''

    @classmethod
    def configure_app(cls):
        cls.application.configure(force=True)
        settings.merge(cls.__configuration__)

    def test_messaging_model(self):
        mockup_messenger = create_messenger()

        # noinspection PyArgumentList
        message = Welcome(
            to='test@example.com',
            subject='Test Subject',
            body={'msg': 'Hello'}
        )

        DBSession.add(message)
        DBSession.commit()

        message.do_({})

        # noinspection PyUnresolvedReferences
        self.assertDictEqual(mockup_messenger.last_message, {
            'body': {'msg': 'Hello'},
            'subject': 'Test Subject',
            'to': 'test@example.com'
        })


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
