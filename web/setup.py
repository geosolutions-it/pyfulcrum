#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def mpath(path_in):
    return os.path.join(*path_in.split('/'))

setup(
    name="PyFulcrum-Webapp",
    version="0.0.1",
    author="GeoSolutions.it/Cezary Statkiewicz",
    author_email="cezary.statkiewicz@geo-solutions.it",
    description=("Fulcrum webapp - webhook and api"),
    license="Propertiary",
    keywords="fulcrum api database webapp webhooks",
    url="https://github.com/geosolutions-it/pyfulcrum/",
    packages=['pyfulcrum.web'],
    setup_requires=['pytest-runner'],
    tests_requires=['pytest'],
    test_packages=['pyfulcrum.web.tests'],
    package_dir={'pyfulcrum': mpath('src/pyfulcrum/'),
                 'pyfulcrum.web': mpath('src/pyfulcrum/web'),
                 'pyfulcrum.web.migrations': mpath('src/pyfulcrum/web/migrations'),
                 'pyfulcrum.web.migrations.versions': mpath('src/pyfulcrum/web/migrations/versions'),
                 'pyfulcrum.web.tests': mpath('src/pyfulcrum/web/tests'),
                 '': 'src'},
    package_data={'pyfulcrum.web.migrations': ['src/pyfulcrum/web/migrations/env',
                                               'src/pyfulcrum/web/migrations/README',
                                               'src/pyfulcrum/web/migrations/script.py.mako',
                                                ],
                 },
    long_description=read('README'),
    classifiers=[
             "Development Status :: 3 - Alpha",
             "Topic :: Utilities",
             "License :: OSI Approved :: BSD License",
    ],
    entry_points = {'console_scripts': [
                    'pyfulcrum = pyfulcrum.web.cli:main'
                    ]
                    },
)
