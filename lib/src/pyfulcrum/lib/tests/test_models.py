#!/usr/bin/env python
# -*- coding: utf-8 -*-


from . import BaseTestCase


class ModelsTestCase(BaseTestCase):
    def test_projects(self):
        p = self.api_manager.create_project(name='test proj', description='test proj')
        self.assertIsNotNone(p)
        self.assertEqual(len(self.api_manager.get_projects()), 1)
