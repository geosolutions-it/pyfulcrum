#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json

from unittest import TestCase, mock
from sqlalchemy import create_engine

from ..api import ApiManager
from ..models import Base, Media
from ..storage import Storage


SQLALCHEMY_ENV = 'TEST_DATABASE_URI'
SQLALCHEMY_CLI = '--test-database-uri'
STORAGE_ENV = 'TEST_STORAGE_ROOT'


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

def get_storage(**kwargs):
    root_dir = os.getenv(STORAGE_ENV) or\
                os.path.join(os.path.dirname(__file__),
                             '..', '..', '..', '..',
                             'examples', 'tests')
    return Storage(root_dir=root_dir, **kwargs)

RESOURCES = ('projects', 'forms', 'records',
             'audio', 'videos', 'photos',
             'fields', 'signatures',)


def mocked_fulcrum_client():
    m = mock.Mock(spec=RESOURCES)
    return m


MOCK_DATA_DIR = os.path.join(os.path.dirname(__file__),
                             '..', '..', '..', '..',
                             'examples', 'api')
STATIC_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__),
                              '..', '..', '..', '..',
                              'examples', 'api', 'static.file'))

class MockedResource(object):

    MEDIA_RESOURCES = ('audio', 'photo', 'video', 'signature',)

    def __init__(self, name):
        self.name = name

    def _get_resource(self, method, obj_id=None):
        args = [self.name, method]
        if obj_id is not None:
            args.append(obj_id)
        path = os.path.abspath(os.path.join(MOCK_DATA_DIR,
                               '{}.json'.format('_'.join(args))))
        with open(path, 'rt') as f:
            data = json.load(f)
            mname = self.name.rstrip('s')
            # for media resources we need to adjust paths to files
            # so they can be fetched with urllib
            if mname in self.MEDIA_RESOURCES and obj_id is not None:
                sizes = Media.SIZES[mname]
                for s in sizes:
                    data[mname][s] = 'file:///{}'.format(STATIC_FILE)
            return data


    def _get_file(self, file_id, size):
        s = StringIO('file: {}, size: {}'.format(file_id, size))
        return s

    def find(self, obj_id):
        return self._get_resource('find', obj_id)

    def search(self, *args, **kwargs):
        return self._get_resource('search')

    def media(self, id, size):
        return self._get_file(id, size)

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
        self._storage = get_storage()
        self.api_manager = ApiManager(self._conn, self._client, self._storage)
        Base.metadata.create_all()

    def tearDown(self):
        self.api_manager.session.rollback()
        Base.metadata.drop_all()
