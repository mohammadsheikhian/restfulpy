import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from os import path, makedirs

from nanohttp import settings, LazyAttribute


_loggers = {}
_handlers = {}
_formatters = {}
root_logger_is_configured = False


def get_level(name):
    return {
        'notset': logging.NOTSET,       # 0
        'debug': logging.DEBUG,         # 10
        'info': logging.INFO,           # 20
        'warning': logging.WARNING,     # 30
        'error': logging.ERROR,         # 40
        'critical': logging.CRITICAL    # 50
    }[name]


def get_filter(level):
    return {
        'debug': DebugFilter,
        'info': InfoFilter,
        'error': ErrorFilter,
        'critical': CriticalFilter,
    }[level]


def ensure_formatter(name):
    if name not in _formatters:
        formatter_config = settings.logging.formatters.default.copy()
        formatter_config.update(settings.logging.formatters.get(name, {}))
        _formatters[name] = logging.Formatter(
            formatter_config.format,
            formatter_config.date_format
        )
    return _formatters[name]


def ensure_handler(name):
    if name not in _handlers:

        handler_config = settings.logging.handlers.default.copy()
        handler_config.update(settings.logging.handlers.get(name, {}))

        if handler_config.type == 'console':
            handler = logging.StreamHandler()
        elif handler_config.type == 'file':

            directory = path.dirname(handler_config.get('filename'))
            if not path.exists(directory):  # pragma: no cover
                makedirs(directory)

            if handler_config.rotate == 'file':
                handler = RotatingFileHandler(
                    handler_config.filename,
                    encoding='utf-8',
                    maxBytes=handler_config.get('max_bytes', 52428800),
                    backupCount=handler_config.get('backup_count', 0)
                )
            elif handler_config.rotate == 'time':
                handler = TimedRotatingFileHandler(
                    handler_config.filename,
                    when=handler_config.get('when', 'h'),
                    interval=handler_config.get('interval', 1),
                    encoding='utf-8',
                    backupCount=handler_config.get('backup_count', 0)
                )

        else:  # pragma: no cover
            raise ValueError('Invalid handler type: %s' % handler_config.type)

        if handler_config.level != 'notset':
            handler.setLevel(get_level(handler_config.level))

        # Attaching newly created formatter to the handler
        handler.setFormatter(ensure_formatter(handler_config.formatter))

        if handler_config.filter_level:
            handler.addFilter(get_filter(level=handler_config.level)())

        _handlers[name] = handler

    return _handlers[name]


def ensure_root_logger():
    global root_logger_is_configured

    if root_logger_is_configured:
        return

    # Rebasing with default config
    logger_config = settings.logging.loggers.default.copy()
    logger_config.update(settings.logging.loggers.root)

    logging.basicConfig(
        handlers=logger_config.handlers,
        level=logger_config.level
    )
    root_logger_is_configured = True


def ensure_logger(name):
    global root_logger_is_configured
    ensure_root_logger()

    if name not in _loggers:
        # Rebasing with default config
        logger_config = settings.logging.loggers.default.copy()
        logger_config.update(settings.logging.loggers.get(name, {}))
        level = get_level(logger_config.level)

        # Creating logger
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = logger_config.propagate

        # Creating Handlers
        for handler_name in logger_config.handlers:
            logger.addHandler(ensure_handler(handler_name))

        # Adding the first log entry
        _loggers[name] = logger

    return _loggers[name]


class LoggerProxy(object):  # pragma: no cover
    def __init__(self, name):
        self.name = name

    @LazyAttribute
    def logger(self):
        return ensure_logger(self.name)

    def info(self, *args, **kw):
        self.logger.info(*args, **kw)

    def debug(self, *args, **kw):
        self.logger.debug(*args, **kw)

    def error(self, *args, **kw):
        self.logger.error(*args, **kw)

    def warning(self, *args, **kw):
        self.logger.warning(*args, **kw)

    def critical(self, *args, **kw):
        self.logger.critical(*args, **kw)

    def exception(self, *args, **kw):
        self.logger.exception(*args, **kw)


def get_logger(logger_name='restfulpy'):
    return LoggerProxy(logger_name)


logger = get_logger()


class InfoFilter(logging.Filter):
    def filter(self, record):
        assert isinstance(record, logging.LogRecord)
        if record.levelno == logging.INFO:
            return record


class DebugFilter(logging.Filter):
    def filter(self, record):
        assert isinstance(record, logging.LogRecord)
        if record.levelno == logging.DEBUG:
            return record


class InfoFilter(logging.Filter):
    def filter(self, record):
        assert isinstance(record, logging.LogRecord)
        if record.levelno == logging.INFO:
            return record


class ErrorFilter(logging.Filter):
    def filter(self, record):
        assert isinstance(record, logging.LogRecord)
        if record.levelno == logging.ERROR:
            return record


class CriticalFilter(logging.Filter):
    def filter(self, record):
        assert isinstance(record, logging.LogRecord)
        if record.levelno == logging.CRITICAL:
            return record

