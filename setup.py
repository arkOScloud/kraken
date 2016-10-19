#!/usr/bin/env python

from setuptools import setup, find_packages

install_requires = [
    'cryptography',
    'eventlet',
    'flask',
    'flask_socketio',
    'itsdangerous',
    'redis'
]


setup(
    name='arkos-kraken',
    version='0.8.1',
    install_requires=install_requires,
    description='arkOS REST API',
    author='CitizenWeb',
    author_email='jacob@citizenweb.io',
    url='http://arkos.io/',
    packages=find_packages(),
    scripts=['krakend']
)
