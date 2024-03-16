import functools
from os.path import exists

from nanohttp import settings, context
from sqlalchemy import create_engine as sa_create_engine, inspect
from sqlalchemy.orm import scoped_session, sessionmaker, Session, \
    declarative_base
from sqlalchemy.sql.schema import MetaData
from alembic import config, command

from .field import Field, relationship, composite, synonym
from .metadata import MetadataField
from .models import BaseModel
from .fulltext_search import to_tsvector, fts_escape
from .types import FakeJSON
from .mixins import ModifiedMixin, SoftDeleteMixin, TimestampMixin, \
    ActivationMixin, PaginationMixin, FilteringMixin, OrderingMixin, \
    ApproveRequiredMixin, FullTextSearchMixin, AutoActivationMixin, \
    DeactivationMixin
from ..helpers import connection_string_redis, generate_shard_key
from ..logging_ import logger


engines = {}


def get_engine_by_shard_key(shard_key):
    global engines
    engine = engines.get(shard_key)
    if engine is None:
        _shard_key = generate_shard_key(shard_key)
        _remote = connection_string_redis().get(_shard_key).decode()
        process_name = settings.context.get('process_name')
        connection_string = f'{_remote}{process_name}_{shard_key}'

        engine = create_engine(connection_string)
        engines[shard_key] = engine
    return engine


class RoutingSession(Session):
    def get_bind(
            self,
            mapper=None,
            clause=None,
            bind=None,
            _sa_skip_events=None,
            _sa_skip_for_implicit_returning=False,
    ):
        engine = None
        shard_key = None

        try:
            if bind is not None:
                engine = bind

            elif not settings.is_database_sharding:
                # return super(RoutingSession, self).get_bind()
                # We should use the master session in this case
                engine = super(RoutingSession, self).get_bind()

            elif hasattr(context, 'shard_key'):
                shard_key = context.shard_key

            if shard_key is not None:
                shard_key = str(shard_key)
                engine = get_engine_by_shard_key(shard_key)

        except Exception as exc:
            logger.critical(exc)

        finally:
            if not engine:
                raise Exception('Can\'t bind session without shard key')

            return engine


# Global session manager: DBSession() returns the Thread-local
# session object appropriate for the current web request.
sharded_session_factory = sessionmaker(
    class_=RoutingSession,
    bind=None,
    autoflush=False,
    autocommit=False,
    expire_on_commit=True,
    twophase=False,
)
DBSession = scoped_session(sharded_session_factory)


# Global session manager: DBSession() returns the Thread-local
# session object appropriate for the current web request.
master_session_factory = sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=True,
    twophase=False,
)
MasterDBSession = scoped_session(master_session_factory)


# Global metadata.
metadata = MetaData()


DeclarativeBase = declarative_base(cls=BaseModel, metadata=metadata)


def create_engine(url=None, echo=None):
    return sa_create_engine(
        url or settings.db.url,
        echo=echo or settings.db.echo
    )


def init_model(engine):
    """
    Call me before using any of the tables or classes in the model.
    :param engine: SqlAlchemy engine to bind the session
    :return:
    """
    MasterDBSession.remove()
    MasterDBSession.configure(bind=engine)

    DBSession.remove()
    DBSession.configure(bind=engine)


def setup_schema(engine=None):
    engine = engine or DBSession.bind
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    has_alembic_version = True if 'alembic_version' in table_names else False

    if not has_alembic_version:
        metadata.create_all(bind=engine)

        if hasattr(settings, 'migration') and \
                exists(settings.migration.directory):

            alembic_cfg = config.Config()
            alembic_cfg.set_main_option(
                "script_location",
                settings.migration.directory,
            )
            alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))
            alembic_cfg.config_file_name = settings.migration.ini
            command.stamp(alembic_cfg, "head")


def create_thread_unsafe_session():
    return sharded_session_factory()


def commit(func):

    @functools.wraps(func)
    def wrapper(*args, **kwargs):

        try:
            if hasattr(context, 'jsonpatch'):
                result = func(*args, **kwargs)
                DBSession.flush()
                return result

            result = func(*args, **kwargs)
            DBSession.commit()
            return result

        except Exception as ex:
            # Actually 200 <= status <= 399 is not an exception and commit must
            # be occurring.
            if hasattr(ex, 'status') and '200' <= str(ex.status) < '400':
                DBSession.commit()
                raise
            if DBSession.is_active:
                DBSession.rollback()
            raise

    return wrapper
