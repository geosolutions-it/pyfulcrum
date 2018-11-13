#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pyfulcrum.web.tests import WebTestCase
from pyfulcrum.web.webhooks import _parse_objects_list

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

    def test_parse_objects_list(self):
        # input, expected output
        tests = (('', {}),
                 ('test', {}),
                 ('test:', {'test': ['']}),
                 ('test:123,345', {'test': ['123', '345']},),
                 ('test:123,345;other', {'test': ['123', '345']},),
                 ('test:123,345;other:aaa-b,cd', {'test': ['123', '345'],
                                                  'other': ['aaa-b', 'cd']},),
                 )
        for input_val, expected_val in tests:
            output_val = _parse_objects_list(input_val)
            self.assertEqual(expected_val, output_val)

    def test_webhook_objects_list_whitelist(self):
        cfg = {'WEBHOOK_TEST_INCLUDE_OBJECTS': 'form:123'}
        cfg.update(self._config)

        self._app.config.from_mapping(cfg)

        resp = self._test_client.post('/webhook/test/',
                                      data='{"type": "form.create", "data": {"id": "7a0c3378-b63a-4707-b459-df499698f23c"}}',
                                      content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data, b'whitelisted', resp.data)


    def test_webhook_objects_list_blacklist(self):
        cfg = {'WEBHOOK_TEST_EXCLUDE_OBJECTS': 'form:7a0c3378-b63a-4707-b459-df499698f23c'}
        cfg.update(self._config)

        self._app.config.from_mapping(cfg)

        resp = self._test_client.post('/webhook/test/',
                                      data='{"type": "form.create", "data": {"id": "7a0c3378-b63a-4707-b459-df499698f23c"}}',
                                      content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data, b'blacklisted', resp.data)
        
        resp = self._test_client.post('/webhook/test/',
                                      data='{"type": "record.create", "data": {"id": "4e1c33ad-5496-4818-826f-504e66239b4d", "form_id":"7a0c3378-b63a-4707-b459-df499698f23c"}}',
                                      content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data, b'blacklisted', resp.data)


    def test_webhook_objects_list_whitelist_ok(self):
        cfg = {'WEBHOOK_TEST_INCLUDE_OBJECTS': 'form:7a0c3378-b63a-4707-b459-df499698f23c'}
        cfg.update(self._config)

        self._app.config.from_mapping(cfg)

        resp = self._test_client.post('/webhook/test/',
                                      data='{"type": "form.create", "data": {"id": "7a0c3378-b63a-4707-b459-df499698f23c"}}',
                                      content_type='application/json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data, b'ok', resp.data)
