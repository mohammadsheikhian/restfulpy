import time
from datetime import datetime, timedelta

from bddcli import Given, Application, status, when, story, given

from restfulpy import Application as RestfulpyApplication
from restfulpy.taskqueue import RestfulpyTask


DBURL = 'postgresql://postgres:postgres@localhost/restfulpy_test'


class WorkerTask(RestfulpyTask):

    __mapper_args__ = {
        'polymorphic_identity': 'worker_task'
    }

    def do_(self, context):
        _task_done.set()


class FooApplication(RestfulpyApplication):
    __configuration__ = f'''
      db:
        url: {DBURL}
    '''


foo = FooApplication(name='Foo')


def foo_main():
    return foo.cli_main()


app = Application('foo', 'tests.test_appcli_renew_worker:foo_main')


def test_appcli_renew_worker_start(db):
    session = db()
    task1 = WorkerTask(
        status='in-progress',
        started_at=datetime.utcnow() - timedelta(minutes=10),
    )
    session.add(task1)

    task2 = WorkerTask(
        status='in-progress',
        started_at=datetime.utcnow() - timedelta(minutes=2),
    )
    session.add(task2)

    task3 = WorkerTask(
        status='success',
        started_at=datetime.utcnow() - timedelta(minutes=10),
    )
    session.add(task3)
    session.commit()

    with Given(app, 'worker renew', nowait=True):
        time.sleep(2)
        story.kill()
        story.wait()
        assert status == -15
        session.refresh(task1)
        assert task1.status == 'new'

        session.refresh(task2)
        assert task2.status == 'in-progress'

        session.refresh(task3)
        assert task3.status == 'success'

        when(given + '--gap 1')
        time.sleep(2)
        story.kill()
        story.wait()
        assert status == -15


if __name__ == '__main__':  # pragma: no cover
    foo.cli_main(['migrate', '--help'])

