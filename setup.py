import re
from os.path import join, dirname

from setuptools import setup, find_packages


# reading package version (without reloading it)
with open(join(dirname(__file__), 'restfulpy', '__init__.py')) as v_file:
    package_version = re.compile(r".*__version__ = '(.*?)'", re.S) \
        .match(v_file.read()) \
        .group(1)


dependencies = [
    'pymlconf >= 1.1, < 3',
    'easycli >= 1.3, < 2',
    'argcomplete',
    'appdirs',
    'sqlalchemy < 3',
    'alembic',
    'itsdangerous <= 2.0.1',
    'mako',
    'psycopg2-binary',
    'redis',
    'pyyaml',
    'sendgrid',
    'ua-parser',
    'user-agents',
    'pycryptodome',
    'python-dateutil',
    'ipinfo',
    'kavenegar',
    'twilio',

    # Testing
    'requests',
    'pytest',
    'bddcli >= 2.4, < 3'
]


setup(
    name='restfulpy',
    version=package_version,
    description='A toolchain for developing REST APIs',
    author='Vahid Mardani',
    author_email='vahid.mardani@gmail.com',
    install_requires=dependencies,
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    license='MIT',
    entry_points={
        'console_scripts': [
            'restfulpy = restfulpy.cli:main'
        ]
    },
)

