import signal
import threading
import time
import traceback
from datetime import datetime, timedelta

from nanohttp import settings
from sqlalchemy import Integer, Enum, Unicode, DateTime, or_, and_
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql.expression import text

from .logging_ import get_logger
from .exceptions import RestfulException
from .orm import TimestampMixin, DeclarativeBase, Field, DBSession, \
    create_thread_unsafe_session


logger = get_logger('taskqueue')


class TaskPopError(RestfulException):
    pass


class MuleTask(TimestampMixin, DeclarativeBase):
    __tablename__ = 'mule_task'

    id = Field(Integer, primary_key=True, json='id')
    at = Field(DateTime, nullable=True, json='at', default=datetime.now)
    status = Field(
        Enum(
            'new',
            'in-progress',
            'expired',
            'success',
            'failed',

            name='mule_status_enum'
        ),
        default='new',
        nullable=True, json='status'
    )
    expired_at = Field(DateTime, nullable=True, json='expiredAt')
    fail_reason = Field(Unicode(4096), nullable=True, json='reason')
    terminated_at = Field(DateTime, nullable=True, json='terminatedAt')
    started_at = Field(DateTime, nullable=True, json='startedAt')
    type = Field(Unicode(50))

    __mapper_args__ = {
        'polymorphic_identity': __tablename__,
        'polymorphic_on': type
    }

    def do_(self):
        raise NotImplementedError

    @classmethod
    def pop(cls, statuses={'new'}, filters=None, session=DBSession):

        find_query = session.query(
            cls.id.label('id'),
            cls.created_at,
            cls.at,
            cls.status,
        )
        if filters is not None:
            find_query = find_query.filter(
                text(filters) if isinstance(filters, str) else filters
            )

        find_query = find_query \
            .filter(cls.at <= datetime.now()) \
            .filter(
                or_(
                    cls.status == 'in-progress', cls.status == 'new', \
                    and_(
                        cls.status == 'failed',
                        cls.expired_at > datetime.now()
                    )
                )
            ) \
            .limit(1) \
            .with_for_update()

        cte = find_query.cte('find_query')
        update_query = MuleTask.__table__.update() \
            .where(MuleTask.id == cte.c.id) \
            .values(
                status='in-progress',
                started_at=datetime.utcnow(),
            ) \
            .returning(MuleTask.__table__.c.id)

        task_id = session.execute(update_query).fetchone()
        session.commit()
        if not task_id:
            raise TaskPopError('There is no task to pop')
        task_id = task_id[0]
        task = session.query(cls).filter(cls.id == task_id).one()
        return task

    def execute(self, context, session=DBSession):
        try:
            isolated_task = session \
                .query(MuleTask) \
                .filter(MuleTask.id == self.id) \
                .one()
            isolated_task.do_(context)
            session.commit()
        except:
            session.rollback()
            raise


def worker(statuses={'new'}, filters=None, tries=-1):
    isolated_session = create_thread_unsafe_session()
    context = {'counter': 0}
    tasks = []

    while True:
        context['counter'] += 1
        try:
            task = MuleTask.pop(
                statuses=statuses,
                filters=filters,
                session=isolated_session
            )

        except TaskPopError as ex:
            isolated_session.rollback()
            if tries > -1:
                tries -= 1
                if tries <= 0:
                    return tasks
            time.sleep(settings.jobs.interval)
            continue

        try:
            task.execute(context)

            # Task success
            task.status = 'success'
            task.terminated_at = datetime.utcnow()

        except Exception as exp:
            task.status = 'failed'
            if task.fail_reason != traceback.format_exc()[-4096:]:
                task.fail_reason = traceback.format_exc()[-4096:]
                logger.critical('Error when executing task: %s' % task.id)
                logger.critical(f'Exception: {exp.__doc__}')

        finally:
            try:
                if isolated_session.is_active:
                    isolated_session.commit()
                tasks.append((task.id, task.status))
            except Exception as exp:
                logger.critical(exp, exc_info=True)
                signal.pthread_kill(threading.get_ident(), signal.SIGKILL)


def renew(session=DBSession):
    while True:
        renew_time_range = datetime.utcnow() - \
            timedelta(minutes=settings.renew_mule_worker.time_range)
        task_id = None

        try:
            task = session.query(MuleTask) \
                .with_for_update() \
                .filter(MuleTask.status == 'in-progress') \
                .filter(MuleTask.started_at <= renew_time_range) \
                .order_by(MuleTask.id) \
                .first()
            if task is None:
                time.sleep(settings.renew_mule_worker.gap)
                continue

            task_id = task.id
            task.status = 'new'
            task.started_at = None
            task.terminated_at = None
            session.commit()
            logger.info(f'Task: {task_id} successfully renewed.')

        except OperationalError as exp:
            logger.critical(exp, exc_info=True)
            break

        except Exception as exp:
            if task_id is not None:
                logger.error(f'Error when renewing task: {task_id}')
            logger.error(exp, exc_info=True)
            session.rollback()

