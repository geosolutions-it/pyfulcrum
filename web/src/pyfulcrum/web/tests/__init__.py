#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
from unittest import mock

from flask import Flask

from pyfulcrum.lib.tests import BaseTestCase

from ..webhooks import webhooks
from ..api import api



class WebTestCase(BaseTestCase):
   
    def setUp(self):
        super().setUp()
        self._config = {"WEBHOOK_TEST_DB": self._conn,
                        "WEBHOOK_TEST_CLIENT": self._client,
                        "WEBHOOK_TEST_STORAGE": self._storage,
                        "API_DB": self._conn,
                        "API_CLIENT": self._client,
                        "API_STORAGE": self._storage}

        self._app = Flask(__name__)
        self._app.config.from_mapping(self._config)
        self._app.register_blueprint(webhooks)
        self._app.register_blueprint(api)
        self._test_client = self._app.test_client()
