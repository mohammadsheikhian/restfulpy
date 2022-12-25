import base64
import importlib.util
import io
import os
import re
import sys
import functools
from hashlib import md5
from mimetypes import guess_type
from os.path import dirname, abspath, split
from urllib.parse import parse_qs

import redis as redis_
from nanohttp import settings
from nanohttp.contexts import Context


_connection_stating_redis = None


def import_python_module_by_filename(name, module_filename):
    """
    Import's a file as a python module, with specified name.

    Don't ask about the `name` argument, it's required.

    :param name: The name of the module to override upon imported filename.
    :param module_filename: The filename to import as a python module.
    :return: The newly imported python module.
    """

    sys.path.append(abspath(dirname(module_filename)))
    spec = importlib.util.spec_from_file_location(
        name,
        location=module_filename)
    imported_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imported_module)
    return imported_module


def construct_class_by_name(name, *args, **kwargs):
    """
    Construct a class by module path name using *args and **kwargs

    Don't ask about the `name` argument, it's required.

    :param name: class name
    :return: The newly imported python module.
    """
    parts = name.split('.')
    module_name, class_name = '.'.join(parts[:-1]), parts[-1]
    module = importlib.import_module(module_name)
    return getattr(module, class_name)(*args, **kwargs)


def to_camel_case(text):
    return re.sub(r'(_\w)', lambda x: x.group(1)[1:].upper(), text)


def copy_stream(source, target, *, chunk_size: int= 16 * 1024) -> int:
    length = 0
    while 1:
        buf = source.read(chunk_size)
        if not buf:
            break
        length += len(buf)
        target.write(buf)
    return length


def md5sum(f):
    if isinstance(f, str):
        file_obj = open(f, 'rb')
    else:
        file_obj = f

    try:
        checksum = md5()
        while True:
            d = file_obj.read(1024)
            if not d:
                break
            checksum.update(d)
        return checksum.digest()
    finally:
        if file_obj is not f:
            file_obj.close()


def split_url(url):
    if '?' in url:
        path, query = url.split('?')
    else:
        path, query = url, ''

    return path, {k: v[0] if len(v) == 1 else v for k, v in parse_qs(
        query,
        keep_blank_values=True,
        strict_parsing=False
    ).items()}


def encode_multipart_data(fields, files, boundary=None):
    boundary = boundary or ''.join([
        '-----',
        base64.urlsafe_b64encode(os.urandom(27)).decode()
    ])
    crlf = b'\r\n'
    lines = []

    if fields:
        for key, value in fields.items():
            lines.append('--' + boundary)
            lines.append('Content-Disposition: form-data; name="%s"' % key)
            lines.append('')
            lines.append(value)

    if files:
        for key, file_path in files.items():
            filename = split(file_path)[1]
            lines.append('--' + boundary)
            lines.append(
                'Content-Disposition: form-data; name="%s"; filename="%s"' %
                (key, filename))
            lines.append(
                'Content-Type: %s' %
                (guess_type(filename)[0] or 'application/octet-stream'))
            lines.append('')
            lines.append(open(file_path, 'rb').read())

    lines.append('--' + boundary + '--')
    lines.append('')

    body = io.BytesIO()
    length = 0
    for l in lines:
        line = (l if isinstance(l, bytes) else l.encode()) + crlf
        length += len(line)
        body.write(line)
    body.seek(0)
    content_type = 'multipart/form-data; boundary=%s' % boundary
    return content_type, body, length


def noneifnone(func):

    @functools.wraps(func)
    def wrapper(value):
        return func(value) if value is not None else None

    return wrapper


def generate_shard_key(shard_key):
    return f'sharding:{shard_key}:connection-string'


def get_connection_string(shard_key, process_name=None):
    if process_name is None:
        process_name = settings.context.get('process_name')

    _shard_key = generate_shard_key(shard_key)
    _remote = connection_string_redis().get(_shard_key).decode()
    return f"{_remote}{process_name}_{shard_key}"


def generate_shard_connection_string(username, password, remote):
    return f'postgresql://{username}:{password}@{remote}/'


def create_blocking_redis():
    return redis_.StrictRedis(
        host=settings.authentication.redis.host,
        port=settings.authentication.redis.port,
        db=settings.authentication.redis.db,
        password=settings.authentication.redis.password
    )


def connection_string_redis():
    global _connection_stating_redis
    if _connection_stating_redis is None:
        _connection_stating_redis = create_blocking_redis()
    return _connection_stating_redis


def get_shard_keys():
    return connection_string_redis().scan_iter(match='*:connection-string')


def with_context(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with Context({}):
            return func(*args, **kwargs)
    return wrapper

