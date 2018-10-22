#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json

from unittest import TestCase, mock
from sqlalchemy import create_engine

from ..api import ApiManager
from ..models import Base


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
        elif (arg.startswith('{}='.format(SQLALCHEMY_CLI)) and
              len(arg) > (len(SQLALCHEMY_CLI)+1)):
            return arg[len(SQLALCHEMY_CLI)+1:]


def get_connection():
    conn_uri = conn_from_env() or conn_from_cli()
    if not conn_uri:
        raise ValueError("No db connection string available.\n"
                         "You can pass it as {} env variable."
                         .format(SQLALCHEMY_ENV)
                         )
    return create_engine(conn_uri)


RESOURCES = ['projects', 'forms', 'records',
             'audio', 'videos', 'pictures',
             'fields',]


def mocked_fulcrum_client():
    m = mock.Mock(spec=RESOURCES)
    return m

MOCK_DATA_DIR = os.path.join(os.path.dirname(__file__),
                             '..', '..', '..', '..',
                             'examples', 'api')

class MockedResource(object):

    def __init__(self, name):
        self.name = name

    def _get_resource(self, method, obj_id=None):
        args = [self.name, method]
        if obj_id is not None:
            args.append(obj_id)
        path = os.path.abspath(os.path.join(MOCK_DATA_DIR, '{}.json'.format('_'.join(args))))
        with open(path, 'rt') as f:
            return json.load(f)
        
    def find(self, obj_id):
        return self._get_resource('find', obj_id)

    def search(self):
        return self._get_resource('search')
        

class MockedFulcrumClient(object):
    
    def __init__(self, *args, **kwargs):
        self.init_resources()

    def init_resources(self):
        for res_name in RESOURCES:
            res = MockedResource(res_name)
            setattr(self, res_name, res)


class BaseTestCase(TestCase):

    def setUp(self):
        self._conn = get_connection()
        self._client = MockedFulcrumClient()
        self.api_manager = ApiManager(self._conn, self._client)
        Base.metadata.create_all()

    def tearDown(self):
        self.api_manager.session.rollback()
        Base.metadata.drop_all()
