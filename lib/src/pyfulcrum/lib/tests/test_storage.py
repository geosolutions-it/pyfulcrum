#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from io import BytesIO
from unittest import TestCase
from . import get_storage
from ..storage import Storage


class StorageTestCase(TestCase):

    def setUp(self):
        self.storage_local = get_storage()
        self.storage_url = get_storage(url_base='http://local/')

    def test_storage_local(self):
        # test is media_type
        # normal is media size
        local_path = self.storage_local.get_path('form_id', 'record_id', 'test', 'normal', 'image/png')
        url_path = self.storage_local.get_url('form_id', 'record_id', 'test', 'normal', 'image/png')
        self.assertTrue(isinstance(local_path, str))
        self.assertTrue(local_path.endswith('form_id/record_id/test_normal.png'), local_path)
        self.assertIsNone(url_path)

    def test_storage_url(self):
        # test is media_type
        # normal is media size
        url_path = self.storage_url.get_url('form_id', 'record_id', 'test', 'normal', 'image/png')
        self.assertTrue(url_path.endswith('form_id/record_id/test_normal.png'), url_path)
        self.assertTrue(url_path.startswith('http://local/'))

    def test_storage_save(self):
        f = BytesIO(b'ffff')
        self.storage_local.save(f, 'form_id', 'record_id', 'test', 'normal', 'image/png')
        local_path = self.storage_local.get_path('form_id', 'record_id', 'test', 'normal', 'image/png')
        f.seek(0)
        with open(local_path, 'rt') as fin:
            self.assertEqual(f.read().decode('utf-8'), fin.read())
