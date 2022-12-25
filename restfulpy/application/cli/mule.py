import signal
import sys

from easycli import SubCommand, Argument
from nanohttp import settings


class StartSubSubCommand(SubCommand):
    __command__ = 'start'
    __help__ = 'Starts the background worker.'
    __arguments__ = [
        Argument(
            '-i',
            '--query-interval',
            type=int,
            default=None,
            help='Gap between run next task(second).',
        ),
        Argument(
            '-s',
            '--status',
            default=[],
            action='append',
            help='Task status to process',
        ),
    ]

    def __call__(self, args):
        from restfulpy.mule import worker

        signal.signal(signal.SIGINT, self.kill_signal_handler)
        signal.signal(signal.SIGTERM, self.kill_signal_handler)

        if not args.status:
            args.status = {'new'}

        if args.query_interval is not None:
            settings.jobs.merge({'interval': args.query_interval})

        print(
            f'The following task types would be processed with of interval'
            f'{settings.jobs.interval}s:'
        )
        print('Tracking task status(es): %s' % ','.join(args.status))

        worker(statuses=args.status)
        print('Press Ctrl+C to terminate worker')

    @staticmethod
    def kill_signal_handler(signal_number, frame):
        print('Terminating')
        sys.stdin.close()
        sys.stderr.close()
        sys.stdout.close()
        sys.exit(signal_number)


class RenewSubSubCommand(SubCommand):
    __command__ = 'renew'
    __help__ = 'Renew in-progress tasks'
    __arguments__ = [
        Argument(
            '-g',
            '--gap',
            type=int,
            default=None,
            help='Gap between run next task.',
        ),
    ]

    def __call__(self, args):
        from restfulpy.mule import renew

        if args.gap is not None:
            settings.renew_mule_worker.merge({'gap': args.gap})

        renew()


class MuleSubCommand(SubCommand):
    __command__ = 'mule'
    __help__ = 'Jobs queue administration'
    __arguments__ = [
        StartSubSubCommand,
        RenewSubSubCommand,
    ]

