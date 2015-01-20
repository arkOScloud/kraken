#!/usr/bin/env python

from distutils.core import setup

setup(
    name='kraken',
    version='0.7',
    install_requires=[
        'redis'
    ],
    description='arkOS REST API',
    author='CitizenWeb',
    author_email='jacob@citizenweb.io',
    url='http://arkos.io/',
    packages=["kraken"]
)
