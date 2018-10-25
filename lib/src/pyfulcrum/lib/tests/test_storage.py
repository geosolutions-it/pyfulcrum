#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from six.moves import StringIO
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
        local_path = self.storage_local.get_path('form_id', 'record_id', 'test', 'normal')
        url_path = self.storage_local.get_url('form_id', 'record_id', 'test', 'normal')
        self.assertTrue(isinstance(local_path, str))
        self.assertTrue(local_path.endswith('form_id/record_id/test_normal'), local_path)
        self.assertIsNone(url_path)


    def test_storage_url(self):
        # test is media_type
        # normal is media size
        url_path = self.storage_url.get_url('form_id', 'record_id', 'test', 'normal')
        self.assertTrue(url_path.endswith('form_id/record_id/test_normal'), url_path)
        self.assertTrue(url_path.startswith('http://local/'))

