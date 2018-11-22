#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pyfulcrum.web.tests import WebTestCase

class ApiTestCase(WebTestCase):

    def test_api(self):
        # this must be commited, because test client uses separate db session
        # and won't see unless it's commited
        with self.api_manager:
            self.api_manager.forms.list(cached=False)
            self.api_manager.records.list(cached=False)
            self.api_manager.photos.list(cached=False)

        self.assertTrue(len(list(self.api_manager.forms.list(cached=True))), 1)
        resp = self._test_client.get('/api/forms/')
        self.assertTrue(resp.status_code, 200)
        self.assertTrue(resp.is_json)
        resp_data = resp.json
        self.assertEqual(resp_data['total'], 1)

        resp = self._test_client.get('/api/forms/?format=raw')
        self.assertTrue(resp.status_code, 200)
        self.assertTrue(resp.is_json)
        resp_data = resp.json
        self.assertEqual(resp_data['total'], 1)

        resp = self._test_client.get('/api/forms/?format=geojson')
        self.assertTrue(resp.status_code, 400)


        resp = self._test_client.get('/api/records/?format=geojson')
        self.assertTrue(resp.status_code, 200)
        self.assertTrue(resp.is_json)
        resp_data = resp.json
        self.assertEqual(resp_data['total'], 1)


        resp = self._test_client.get('/api/records/?format=geojson&page=1')
        self.assertTrue(resp.status_code, 200)
        self.assertTrue(resp.is_json)
        resp_data = resp.json
        self.assertEqual(resp_data['total'], 1)
        self.assertEqual(len(resp_data['features']), 0)


        resp = self._test_client.get('/api/records/?format=kml')
        self.assertTrue(resp.status_code, 200)
        self.assertFalse(resp.is_json)
        self.assertTrue(resp.data.startswith(b'<?xml '))

        resp = self._test_client.get('/api/records/?format=shp')
        self.assertTrue(resp.status_code, 200)
        self.assertFalse(resp.is_json)
        self.assertTrue(resp.data.startswith(b'PK'))

        resp = self._test_client.get('/api/records/?format=invalid')
        self.assertTrue(resp.status_code, 400)

        resp = self._test_client.get('/api/records/?format=csv')
        self.assertTrue(resp.status_code, 200)
        self.assertFalse(resp.is_json)
        self.assertTrue(resp.data.startswith(b'"id","altitude",'))

