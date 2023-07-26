import argparse
import os
from os.path import join

from alembic.config import main as alembic_main
from easycli import SubCommand, Argument
from nanohttp import settings


class MigrateSubCommand(SubCommand):
    __command__ = 'migrate'
    __help__ = 'Executes the alembic command'
    __arguments__ = [
        Argument(
            'alembic_args',
            nargs=argparse.REMAINDER,
            help='For more information, please see `alembic --help`',
        ),
        Argument(
            '-k',
            '--shard_keys',
            default=None,
            action='append',
            help='Shard keys you want to migrate, Example: -k 1 -k 2',
        ),
        Argument(
            '-s',
            '--skip_master',
            action='store_true',
            default=False,
            help="set true if you don't want to migrate master database",
        ),
    ]

    def __call__(self, args):
        current_directory = os.curdir
        try:
            settings.migration.shard_database = args.shard_keys
            settings.migration.skip_master = args.skip_master

            os.chdir(args.application.root_path)
            alembic_ini = join(args.application.root_path, 'alembic.ini')
            alembic_main(argv=['--config', alembic_ini] + args.alembic_args)

        finally:
            os.chdir(current_directory)

