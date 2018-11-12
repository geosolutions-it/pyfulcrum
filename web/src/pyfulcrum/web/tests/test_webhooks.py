#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pyfulcrum.web.tests import WebTestCase

class WebhookTestCase(WebTestCase):

    def test_webhook_errors(self):
        resp = self._test_client.get('/webhook/test')
        self.assertEqual(resp.status_code, 405)

        resp = self._test_client.post('/webhook/invalid/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(b'empty payload', resp.data)
        # self.assertEqual(b'webhook invalid configuration not found', resp.data)

        resp = self._test_client.post('/webhook/test/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(b'empty payload', resp.data)

        resp = self._test_client.post('/webhook/test/', data='{}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(b'empty json payload', resp.data)


        resp = self._test_client.post('/webhook/test/', data='{"type": "some.invalid"}', content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        resp = self._test_client.post('/webhook/test/', data='{"type": "some.invalid"}', content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(b'cannot handle some.invalid event type', resp.data, resp.data)

        resp = self._test_client.post('/webhook/test/', data='{"type": "form.create"}', content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(b'with empty object id' in resp.data, resp.data)


        resp = self._test_client.post('/webhook/invalid/',
                                      data='{"type": "form.create", "data": {"id": "7a0c3378-b63a-4707-b459-df499698f23c"}}',
                                      content_type='application/json')
        self.assertEqual(resp.status_code, 404, resp.data)
        self.assertTrue(b'webhook invalid configuration not found' in resp.data, resp.data)



    def test_webhook_processing(self):
        resp = self._test_client.post('/webhook/test/',
                                      data='{"type": "form.create", "data": {"id": "7a0c3378-b63a-4707-b459-df499698f23c"}}',
                                      content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data, b'ok')

        form = self.api_manager.forms.get("7a0c3378-b63a-4707-b459-df499698f23c", cached=True)
        self.assertEqual(form.id, "7a0c3378-b63a-4707-b459-df499698f23c")
