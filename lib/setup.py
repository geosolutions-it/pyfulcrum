#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


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
    package_dir={'pyfulcrum': os.path.join(*('src/pyfulcrum/').split('/')),
                 'pyfulcrum.lib': os.path.join(*('src/pyfulcrum/lib')
                                               .split('/')),
                 'pyfulcrum.lib.tests':
                 os.path.join(*('src/pyfulcrum/lib/tests').split('/')),
                 '': 'src'},
    long_description=read('README'),
    classifiers=[
             "Development Status :: 3 - Alpha",
             "Topic :: Utilities",
             "License :: OSI Approved :: BSD License",
    ],
)
