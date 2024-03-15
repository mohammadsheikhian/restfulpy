import time
import traceback
from datetime import datetime, timedelta

from nanohttp import settings, context as ctx
from sqlalchemy import Integer, Enum, Unicode, DateTime
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql.expression import text

from .constants import RESTFULPY_TASK_NEW, RESTFULPY_TASK_SUCCESS, \
    RESTFULPY_TASK_IN_PROGRESS, RESTFULPY_TASK_FAILED
from .helpers import get_shard_keys, with_context
from .logging_ import get_logger
from .exceptions import RestfulException
from .orm import TimestampMixin, DeclarativeBase, Field, DBSession, \
    create_thread_unsafe_session


logger = get_logger('taskqueue')


class TaskPopError(RestfulException):
    pass


class MaxRetriesExceededError(RestfulException):
    pass


class RestfulpyTask(TimestampMixin, DeclarativeBase):
    __tablename__ = 'restfulpy_task'

    __max_retries__ = None  # set to None to not apply max_reties on the tasks.

    id = Field(
        Integer,
        primary_key=True,
        json='id',
    )
    priority = Field(
        Integer,
        nullable=False,
        default=50,
        json='priority',
    )
    status = Field(
        Enum(
            RESTFULPY_TASK_NEW,
            RESTFULPY_TASK_SUCCESS,
            RESTFULPY_TASK_IN_PROGRESS,
            RESTFULPY_TASK_FAILED,
            name='task_status_enum'
        ),
        default='new',
        nullable=True,
        json='status',
    )
    fail_reason = Field(
        Unicode(4096),
        nullable=True,
    )
    started_at = Field(
        DateTime,
        nullable=True,
    )
    terminated_at = Field(
        DateTime,
        nullable=True,
    )
    type = Field(Unicode(50))
    retries = Field(
        Integer,
        nullable=False,
        default=0,
    )

    __mapper_args__ = {
        'polymorphic_identity': __tablename__,
        'polymorphic_on': type
    }

    def do_(self):
        raise NotImplementedError

    @classmethod
    def pop(
            cls,
            statuses={RESTFULPY_TASK_NEW},
            filters=None,
            session=DBSession,
    ):

        find_query = session.query(
            cls.id.label('id'),
            cls.created_at,
            cls.status,
            cls.type,
            cls.priority
        )
        if filters is not None:
            find_query = find_query.filter(
                text(filters) if isinstance(filters, str) else filters
            )

        find_query = find_query \
            .filter(cls.status.in_(statuses)) \
            .order_by(cls.priority.desc()) \
            .order_by(cls.created_at) \
            .limit(1) \
            .with_for_update()

        cte = find_query.cte('find_query')

        update_query = RestfulpyTask.__table__.update() \
            .where(RestfulpyTask.id == cte.c.id) \
            .values(
                status=RESTFULPY_TASK_IN_PROGRESS,
                started_at=datetime.utcnow(),
                retries=RestfulpyTask.retries + 1,
            ) \
            .returning(RestfulpyTask.__table__.c.id)

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
                .query(RestfulpyTask) \
                .filter(RestfulpyTask.id == self.id) \
                .one()
            if isolated_task.__max_retries__ is not None and \
                    isolated_task.retries >= isolated_task.__max_retries__:
                raise MaxRetriesExceededError()

            isolated_task.do_(context)
            session.commit()
        except:
            session.rollback()
            raise

    @classmethod
    @with_context
    def cleanup(cls, time_limitation, session=DBSession):
        shard_keys = [b'sharding:test:connection-string']
        if settings.is_database_sharding:
            shard_keys = get_shard_keys()

        for shard_key in shard_keys:
            shard_key = shard_key.decode()
            shard_key = shard_key.replace(':connection-string', '')
            shard_key = shard_key.replace('sharding:', '')
            ctx.shard_key = shard_key

            to_clean_ids = session.query(RestfulpyTask.id) \
                .filter(RestfulpyTask.started_at < time_limitation) \
                .filter(RestfulpyTask.status == RESTFULPY_TASK_SUCCESS)

            for task_class in RestfulpyTask.__subclasses__():
                session.query(task_class) \
                    .filter(task_class.id.in_(to_clean_ids)) \
                    .delete(synchronize_session=False)
                session.commit()

            session.query(RestfulpyTask) \
                .filter(RestfulpyTask.id.in_(to_clean_ids)) \
                .delete(synchronize_session=False)
            session.commit()

    @classmethod
    def reset_status(
            cls,
            task_id,
            session=DBSession,
            statuses=[RESTFULPY_TASK_IN_PROGRESS],
    ):
        session.query(RestfulpyTask) \
            .filter(RestfulpyTask.status.in_(statuses)) \
            .filter(RestfulpyTask.id == task_id) \
            .with_for_update() \
            .update({
                'status': RESTFULPY_TASK_NEW,
                'started_at': None,
                'terminated_at': None
            }, synchronize_session='fetch')


@with_context
def worker(statuses={RESTFULPY_TASK_NEW}, filters=None, tries=-1):
    isolated_session = create_thread_unsafe_session()
    context = {'counter': 0}
    tasks = []
    shard_keys = [b'sharding:test:connection-string']

    while True:
        if settings.is_database_sharding:
            shard_keys = get_shard_keys()

        for shard_key in shard_keys:
            shard_key = shard_key.decode()
            shard_key = shard_key.replace(':connection-string', '')
            shard_key = shard_key.replace('sharding:', '')
            ctx.shard_key = shard_key

            context['counter'] += 1

            try:
                task = RestfulpyTask.pop(
                    statuses=statuses,
                    filters=filters,
                    session=isolated_session
                )
                assert task is not None

            except TaskPopError as ex:
                isolated_session.rollback()
                if tries > -1:
                    tries -= 1
                    if tries <= 0:
                        return tasks
                continue

            except Exception as exp:
                logger.error(f'Error when popping task. {exp.__doc__}')
                raise exp

            try:
                task.execute(context)

                # Task success
                task.status = RESTFULPY_TASK_SUCCESS
                task.terminated_at = datetime.utcnow()

            except MaxRetriesExceededError as exp:
                task.status = RESTFULPY_TASK_FAILED
                # task.fail_reason = traceback.format_exc()[-4096:]

            except Exception as exp:
                task.status = 'new'
                if task.fail_reason != traceback.format_exc()[-4096:]:
                    task.fail_reason = traceback.format_exc()[-4096:]
                    logger.critical(dict(
                        message=f'Error when executing task: {task.id}',
                        taskId=task.id,
                        exception=exp.__doc__,
                        failReason=task.fail_reason,
                        shardKey=shard_key,
                    ))

            finally:
                try:
                    if isolated_session.is_active:
                        isolated_session.commit()

                    tasks.append((task.id, task.status))
                except Exception as exp:
                    logger.critical(exp, exc_info=True)
        time.sleep(settings.worker.gap)


@with_context
def renew(session=DBSession):
    shard_keys = [b'sharding:test:connection-string']

    while True:
        renew_time_range = datetime.utcnow() - \
            timedelta(minutes=settings.renew_worker.time_range)

        if settings.is_database_sharding:
            shard_keys = get_shard_keys()

        for shard_key in shard_keys:
            shard_key = shard_key.decode()
            shard_key = shard_key.replace(':connection-string', '')
            shard_key = shard_key.replace('sharding:', '')
            ctx.shard_key = shard_key

            task_id = None
            try:
                task = session.query(RestfulpyTask) \
                    .with_for_update() \
                    .filter(
                        RestfulpyTask.status == RESTFULPY_TASK_IN_PROGRESS,
                        RestfulpyTask.started_at <= renew_time_range
                    ) \
                    .order_by(RestfulpyTask.id) \
                    .first()
                if task is None:
                    continue

                task_id = task.id
                task.status = RESTFULPY_TASK_NEW
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
        time.sleep(settings.renew_worker.gap)

