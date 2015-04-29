#!/usr/bin/env python

from setuptools import setup, find_packages


setup(
    name='arkos-kraken',
    version='0.7.0beta2',
    install_requires=[
        'redis',
        'itsdangerous'
    ],
    description='arkOS REST API',
    author='CitizenWeb',
    author_email='jacob@citizenweb.io',
    url='http://arkos.io/',
    packages=find_packages(),
    scripts=['krakend']
)
