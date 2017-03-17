#!/usr/bin/env python

import os

from pip.req import parse_requirements
from setuptools import setup

install_reqs = parse_requirements(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                               'requirements.txt'), session='None')

setup(
    name='apsconnectcli',
    author='Alexander Khaerov',
    version=1,
    extras_require={
        ':python_version<="2.7"': ['backports.tempfile==1.0rc1']},
    packages=['apsconnectcli'],
    description='A command line tool for creation aps-frontend instance',
    url='http://odin.com',
    license='License :: Other/Proprietary License',
    install_requires=[str(ir.req) for ir in install_reqs],
    entry_points={
        'console_scripts': [
            'apsconnect = apsconnectcli.apsconnect:main',
        ]
    }
)
