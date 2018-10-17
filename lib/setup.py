#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def mpath(path_in):
    return os.path.join(*path_in.split('/'))

setup(
    name="PyFulcrum-lib",
    version="0.0.1",
    author="GeoSolutions.it/Cezary Statkiewicz",
    author_email="cezary.statkiewicz@geo-solutions.it",
    description=("Fulcrum Backup module - handles basic I/O of data"),
    license="Propertiary",
    keywords="fulcrum api database",
    url="https://github.com/geosolutions-it/pyfulcrum/",
    packages=['pyfulcrum.lib'],
    setup_requires=['pytest-runner'],
    tests_requires=['pytest'],
    test_packages=['pyfulcrum.lib.tests'],
    package_dir={'pyfulcrum': mpath('src/pyfulcrum/'),
                 'pyfulcrum.lib': mpath('src/pyfulcrum/lib'),
                 'pyfulcrum.lib.migrations': mpath('src/pyfulcrum/lib/migrations'),
                 'pyfulcrum.lib.migrations.versions': mpath('src/pyfulcrum/lib/migrations/versions'),
                 'pyfulcrum.lib.tests': mpath('src/pyfulcrum/lib/tests'),
                 '': 'src'},
    package_data={'pyfulcrum.lib.migrations': ['src/pyfulcrum/lib/migrations/env',
                                               'src/pyfulcrum/lib/migrations/README',
                                               'src/pyfulcrum/lib/migrations/script.py.mako',
                                                ]
    long_description=read('README'),
    classifiers=[
             "Development Status :: 3 - Alpha",
             "Topic :: Utilities",
             "License :: OSI Approved :: BSD License",
    ],
)
