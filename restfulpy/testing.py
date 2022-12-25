import os
import re
import uuid
from os import path

import pytest
from bddrest import Given, when
from nanohttp import settings
from restfulpy.db import PostgreSQLManager
from restfulpy.helpers import generate_shard_key, connection_string_redis, \
    get_connection_string
from restfulpy.orm import master_session_factory, MasterDBSession, \
    DBSession, engines, get_engine_by_shard_key
from sqlalchemy.orm.session import close_all_sessions
from sqlalchemy.orm import sessionmaker, scoped_session

import restfulpy
from .configuration import configure
from .db import PostgreSQLManager as DBManager
from .mockup import MockupApplication
from .orm import setup_schema, sharded_session_factory, create_engine, \
    init_model


LEGEND = '''

### Legend

#### Pagination

| Param  | Meaning            |
| ------ | ------------------ |
| take   | Rows per page      |
| skip   | Skip N rows        |

#### Search & Filtering

You can search and filter the result via query-string:

```
/path/to/resotrce?field=[op]value1[,value2]
```

| Operator  | Meaning | Example         |
| --------- | ------- | --------------- |
|           | =       | id=2            |
| !         | !=      | id=!2           |
| >         | >       | id=>2           |
| >=        | >=      | id=>=2          |
| <         | <       | id=<2           |
| <=        | <=      | id=<=2          |
| %         | LIKE    | title=u%s       |
| ~,%       | ILIKE   | title=~u%s      |
| IN()      | IN      | id=IN(2,3,4)    |
| !IN()     | NOT IN  | id=!IN(2,3,4)   |
| BETWEEN() | BETWEEN | id=BETWEEN(2,9) |

#### Sorting

You can sort like this:

```
/path/to/resource?sort=[op]value
```

| Operator  | Meaning |
| --------- | ------- |
|           | ASC     |
| \\-        | DESC    |

'''


@pytest.fixture(scope='function', params=[''])
def db(request):
    _configuration = '''
    db:
      test_url: postgresql://postgres:postgres@localhost/restfulpy_test
      administrative_url: postgresql://postgres:postgres@localhost/postgres
    '''
    configure(force=True)
    settings.merge(_configuration)
    if isinstance(request, str) or request.param != '':
        settings.merge(request.param)

    # Overriding the db uri because this is a test session, so db.test_uri will
    # be used instead of the db.uri
    settings.db.url = settings.db.test_url

    # Drop the previously created db if exists.
    with DBManager(url=settings.db.test_url) as m:
        m.drop_database()
        m.create_database()

    # An engine to create db schema and bind future created sessions
    engine = create_engine()

    # A session factory to create and store session to close it on tear down
    sessions = []

    def _connect(*a, expire_on_commit=False, **kw):
        new_session = sharded_session_factory(
            bind=engine,
            *a,
            expire_on_commit=expire_on_commit,
            **kw
        )
        sessions.append(new_session)
        return new_session

    session = _connect(expire_on_commit=True)

    # Creating database objects
    setup_schema(session.bind)
    session.commit()

    # Closing the session to free the connection for future sessions.
    session.close()

    # Preparing and binding the application shared scoped session, due some
    # errors when a model trying to use the mentioned session internally.
    init_model(engine)

    yield _connect

    # Closing all sessions created by the test writer
    for s in sessions:
        s.close()

    close_all_sessions()
    engine.dispose()

    # Dropping the previously created database
    with DBManager(url=settings.db.test_url) as m:
        m.drop_database()


class TestCase:
    pass


class ApplicableTestCase:
    __application__ = None
    __application_factory__ = MockupApplication
    __controller_factory__ = None
    __configuration__ = None
    __story_directory__ = None
    __api_documentation_directory__ = None
    _engines = {}
    _master_engine = None
    _sessions = []
    _authentication_token = None
    __metadata__ = None
    __session = None

    @classmethod
    def configure_application(cls):
        cls.__application__.configure(force=True)

        if cls.__configuration__:
            settings.merge(cls.__configuration__)

        # Overriding the db uri because this is a test session, so db.test_uri
        # will be used instead of the db.uri
        settings.db.url = settings.db.test_url

    @classmethod
    def create_session(cls, *a, shard_key=None, expire_on_commit=False, **kw):
        shard_key = str(shard_key) if shard_key else None
        if shard_key is None:
            engine = cls._master_engine
        else:
            engine = cls._engines.get(shard_key)

        if not engine:
            process_name = settings.context.get('process_name')
            url = settings.db.test_url.split('/')
            url = '/'.join(url[:-1])
            url = f'{url}/{process_name}_{shard_key}'
            engine = create_engine(url=url)
            cls._engines[shard_key] = engine

        new_session = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            twophase=False,
        )

        new_session = scoped_session(new_session)
        cls._sessions.append(new_session)
        return new_session

    @classmethod
    def create_master_session(cls, *a, expire_on_commit=False, **kw):
        new_session = master_session_factory(
            bind=cls._master_engine,
            *a,
            expire_on_commit=expire_on_commit,
            **kw
        )
        cls._sessions.append(new_session)
        return new_session

    @property
    def _session(self):
        if self.__session is None:
            self.__session = self.create_session()

        return self.__session

    @classmethod
    def initialize_orm(cls):
        # Drop the previously created db if exists.
        with DBManager(url=settings.db.test_url) as m:
            m.drop_database()
            m.create_database()

        engine = create_engine(url=settings.db.test_url)
        cls._master_engine = engine
        session = cls.create_master_session(expire_on_commit=False)
        setup_schema(cls._master_engine)
        session.commit()
        session.close()

        cls.__application__.initialize_orm()

    @classmethod
    def mockup(cls):
        """This is a template method so this is optional to override and you
        haven't called the super when overriding it, because there isn't any.
        """
        pass

    @classmethod
    def cleanup_orm(cls):
        # Closing all sessions created by the test writer
        while True:
            try:
                s = cls._sessions.pop()
                s.close()
            except IndexError:
                break

        MasterDBSession.remove()
        DBSession.remove()

        if MasterDBSession.bind is not None:
            MasterDBSession.bind.dispose()

        if cls._master_engine is not None:
            cls._master_engine.dispose()

        for k, engine in engines.items():
            if engine is not None:
                engine.dispose()

        for k, engine in cls._engines.items():
            if engine is not None:
                engine.dispose()

        # Dropping the previously created database
        with DBManager(url=settings.db.test_url) as m:
            m.drop_database()

        for k, engine in cls._engines.items():
            # Dropping the previously created database
            with DBManager(url=str(engine.url)) as m:
                m.drop_database()

    @classmethod
    def setup_class(cls):
        if cls.__application__ is None:
            parameters = {}
            if cls.__controller_factory__ is not None:
                parameters['root'] = cls.__controller_factory__()

            cls.__application__ = cls.__application_factory__(
                'Restfulpy testing application',
                **parameters,
            )

        cls.configure_application()
        try:
            cls.initialize_orm()
            cls.mockup()
        except Exception as e:
            cls.teardown_class()
            raise e

    @classmethod
    def teardown_class(cls):
        cls.cleanup_orm()
        cls.copy_legend()

    @classmethod
    def copy_legend(cls):
        if cls.__api_documentation_directory__ is None:
            return

        os.makedirs(cls.__api_documentation_directory__, exist_ok=True)
        target_filename = path.join(
            cls.__api_documentation_directory__,
            f'LEGEND-restfulpy--v{restfulpy.__version__}.md',
        )
        if path.exists(target_filename):
            return

        with open(target_filename, 'w') as f:
            f.write(LEGEND)

    @classmethod
    def _ensure_directory(cls, d):
        if not path.exists(d):
            os.makedirs(d, exist_ok=True)

    @classmethod
    def _get_document_filename(cls, directory, story):
        cls._ensure_directory(directory)
        title = story.title.lower().replace(' ', '-')
        title = title.replace('/', '-or-')

        url_parts = story.base_call.url.split('/')
        if len(url_parts) >= 3:
            entity = '_'.join(
                p for p in url_parts[2:] if p and not p.startswith(':')
            )
        elif len(url_parts) == 2:
            entity = 'root'
        else:
            raise ValueError(
                'Url should be started with /apiv1/ following entity name'
            )

        filename = path.join(
            directory,
            f'{story.base_call.verb}-{entity}--{title}'
        )
        return filename

    @classmethod
    def _get_story_filename(cls, story):
        filename = cls._get_document_filename(cls.__story_directory__, story)
        return f'{filename}.yml'

    @classmethod
    def _get_markdown_filename(cls, story):
        filename = cls._get_document_filename(
            cls.__api_documentation_directory__,
            story
        )
        return f'{filename}.md'

    @classmethod
    def _get_field_info(cls, resource, verb, name):
        for k in cls.__metadata__:
            if re.match(k, resource):
                return cls.__metadata__[k].get(name)
        return None

    def given(self, *a, autodoc=True, **kw):
        if self._authentication_token is not None:
            kw.setdefault('authorization', self._authentication_token)

        if self.__story_directory__:
            kw['autodump'] = self._get_story_filename

        if autodoc and self.__api_documentation_directory__:
            kw['autodoc'] = self._get_markdown_filename

        if self.__metadata__:
            kw['fieldinfo'] = self._get_field_info

        return Given(self.__application__, *a, **kw)

    def when(self, *a, **kw):
        if self._authentication_token is not None:
            kw.setdefault('authorization', self._authentication_token)
        return when(*a, **kw)

    def login(self, form, url='/apiv1/sessions', verb='POST'):
        with self.given(
                None,
                url,
                verb,
                form=form
        ) as story:
            response = story.response
            assert response.status == '200 OK'
            assert 'token' in response.json
            self._authentication_token = response.json['token']

    def logout(self):
        self._authentication_token = None

    @classmethod
    def initialize_shard_db(cls, shard_key):
        settings.is_database_sharding = True

        test_url_parts = settings.db.test_url.split('/')
        database_connection_string = '/'.join(test_url_parts[:-1]) + '/'

        _shard_key = generate_shard_key(shard_key)
        _redis = connection_string_redis()
        _redis.set(_shard_key, database_connection_string)

        database_connection_string = get_connection_string(shard_key)
        with PostgreSQLManager(database_connection_string) as db_admin:
            db_admin.drop_database()
            db_admin.create_database()
            engine = get_engine_by_shard_key(str(shard_key))
            setup_schema(engine)


class UUID1Freeze:
    _original = None

    def __init__(self, uuid_):
        self.uuid = uuid_

    def __enter__(self):
        self._original = uuid.uuid1
        uuid.uuid1 = lambda: self.uuid

    def __exit__(self, exc_type, exc_value, traceback):
        uuid.uuid1 = self._original
        self._original = None

