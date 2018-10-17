#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse

from unittest import TestCase
from sqlalchemy import create_engine

from ..api import ApiManager
from ..models import *


SQLALCHEMY_ENV = 'TEST_DATABASE_URI'
SQLALCHEMY_CLI = '--test-database-uri'
def conn_from_env():
    return os.getenv(SQLALCHEMY_ENV)
        
def conn_from_cli():
    next_arg = False
    for arg in sys.argv:
        if next_arg:
            return arg
        if arg == SQLALCHEMY_CLI:
            next_arg = True
        elif arg.startswith('{}='.format(SQLALCHEMY_CLI))\
            and len(arg)> (len(SQLALCHEMY_CLI)+1):
            return arg[len(SQLALCHEMY_CLI)+1:]
        
def get_connection():
    conn_uri = conn_from_env() or conn_from_cli()
    if not conn_uri:
        raise ValueError("No connection string available")
    return create_engine(conn_uri)



class BaseTestCase(TestCase):

    def setUp(self):
        self._conn = get_connection()
        self.api_manager = ApiManager(self._conn)
        Base.metadata.create_all()

    def tearDown(self):
        self.api_manager.session.rollback()
        Base.metadata.drop_all()

