from os import path

from nanohttp import configure as nanohttp_configure, settings


__builtin_config = """

debug: true
is_testing: false
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
  skip_master: False

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

sms:
  default_provider:
    name: restfulpy.messaging.sms.ConsoleSmsProvider
    api_key: <API-key>
    url: <url>
    sender: <sender>
    reference: <reference>
    channel: <channel>
  
  providers:
    98:
      name: restfulpy.messaging.sms.ConsoleSmsProvider
      api_key: <API-key>
      url: <url>
      sender: <sender>
      reference: <reference>
      channel: <channel>

geo_ip:
  access_token: <access token>
  # default_getter: restfulpy.geolocation.providers.IpApiProvider
  default_getter: restfulpy.geolocation.providers.IpInfoProvider
  is_active: False
  time_out: 2 # Seconds
  ttl: 5184000 # 60*24*3600 Seconds
  maxsize: 4000

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

redis:
  host: localhost
  port: 6379
  password: ~

rabbitmq:
  host: localhost
  port: 5672
  account:
    username: guest
    password: guest
"""


def configure(context=None, force=False):

    context = context or {}
    context['restfulpy_root'] = path.dirname(__file__)

    nanohttp_configure(
        context=context,
        force=force
    )
    settings.merge(__builtin_config)

