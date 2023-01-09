from os import path

from nanohttp import configure as nanohttp_configure, settings


__builtin_config = """

debug: true
timestamp: false
# Default timezone.
# empty for local time
# 0, utc, UTC, z or Z for the UTC,
# UTC±HH:MM for specify timezone. ie. +3:30 for tehran
# An instance of datetime.tzinfo is also acceptable
# Example:
# timezone: !!python/object/apply:datetime.timezone
#   - !!python/object/apply:datetime.timedelta [0, 7200, 0]
#   - myzone
timezone:

is_database_sharding: false

db:
  # The main uri
  url: postgresql://postgres:postgres@localhost/restfulpy_demo

  # Will be used to create and drop database(s).
  administrative_url: postgresql://postgres:postgres@localhost/postgres

  # Will be used to run tests
  test_url: postgresql://postgres:postgres@localhost/restfulpy_test

  # Redirect all SQL Queries to std-out
  echo: false

migration:
  directory: migration
  ini: alembic.ini
  shard_database: ~

jwt:
  secret: JWT-SECRET
  system_message_secret: SYSTEM-MESSAGE-SECRET
  algorithm: HS256
  max_age: 86400  # 24 Hours
  refresh_token:
    secret: JWT-REFRESH-SECRET
    algorithm: HS256
    max_age: 2678400  # 30 Days
    secure: true
    httponly: false
    # path: optional
    #path: /

messaging:
  # default_messenger: restfulpy.messaging.providers.SMTPProvider
  # default_messenger: restfulpy.messaging.providers.SendGridProvider
  default_messenger: restfulpy.messaging.ConsoleMessenger
  default_sender: restfulpy
  mako_modules_directory:
  template_dirs:
    - %(restfulpy_root)s/messaging/templates
  api_key: API_KEY

geo_ip:
  access_token: <access token>
  # default_getter: restfulpy.geolocation.providers.IpApiProvider
  default_getter: restfulpy.geolocation.providers.IpInfoProvider
  is_active: False

templates:
  directories: []

authentication:
  redis:
    host: localhost
    port: 6379
    password: ~
    db: 0

worker:
  gap: .5
  number_of_threads: 1
  cleanup_time_limitation: 10 # Days

renew_worker:
  time_range: 5 # Minutes
  gap: 300 # Seconds

renew_mule_worker:
  time_range: 5 # Minutes
  gap: 300 # Seconds

jobs:
  interval: .5 # Seconds
  number_of_threads: 1

smtp:
  host: smtp.example.com
  port: 587
  username: user@example.com
  password: password
  local_hostname: localhost
  tls: true
  auth: true
  ssl: false
  
# Logging stuff
logging:
  loggers:
    default:
      handlers:
        - default
      level: debug
      formatter: default
      propagate: true
      
    root:
      level: debug
      formatter: default
      
  handlers:
    default:
      level: notset
      filter_level: false
      max_bytes: 52428800
      backup_count: 2
      formatter: default
      type: console
      rotate: time
      when: s
      interval: 1
      filename: /var/log/restfulpy.log
      
    console:
      type: file
      
  formatters:
    default:
      format: "%%(asctime)s - %%(name)s - %%(levelname)s - %%(message)s"
      date_format: "%%Y-%%m-%%d %%H:%%M:%%S"

"""


def configure(context=None, force=False):

    context = context or {}
    context['restfulpy_root'] = path.dirname(__file__)

    nanohttp_configure(
        context=context,
        force=force
    )
    settings.merge(__builtin_config)

