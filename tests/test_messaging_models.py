from nanohttp import settings

from restfulpy.messaging import Email, create_messenger


def test_messaging_model(db):
    __configuration__ = '''
    messaging:
      default_sender: test@example.com
      default_messenger: restfulpy.mockup.MockupMessenger
    '''

    settings.merge(__configuration__)
    session = db()

    mockup_messenger = create_messenger()

    message = Email(
        to='test@example.com',
        subject='Test Subject',
        body={'msg': 'Hello'}
    )

    session.add(message)

    message2 = Email(
        to='test2@example.com',
        subject='Test Subject 2',
        body={'msg': 'Hello'}
    )

    session.add(message2)

    message3 = Email(
        to='test3@example.com',
        subject='Test Subject 3',
        body={'msg': 'Hello'}
    )

    session.add(message3)
    session.commit()

    message.do_({'counter': 1}, {})
    message2.do_({'counter': 1}, {})
    message3.do_({'counter': 1}, {})

    assert mockup_messenger.last_message == {
        'body': {'msg': 'Hello'},
        'subject': 'Test Subject 3',
        'to': 'test3@example.com'
    }
    assert mockup_messenger.count == 3

