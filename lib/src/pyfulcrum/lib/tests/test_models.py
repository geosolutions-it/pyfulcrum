#!/usr/bin/env python
# -*- coding: utf-8 -*-


from . import BaseTestCase


class ModelsTestCase(BaseTestCase):
    def test_projects(self):
        p = self.api_manager.create_project(id='aaa',
                                            name='test proj',
                                            description='test proj')
        self.assertIsNotNone(p)
        self.assertEqual(len(self.api_manager.get_projects()), 1)
        self.assertEqual(len(self.api_manager.projects.list()), 1)
        self.assertEqual(len(self.api_manager.projects.list(cached=False)), 2)
        projects = self.api_manager.get_projects()
        self.assertEqual(len(projects), 2, projects)

    def test_forms(self):

        self.assertEqual(len(self.api_manager.forms.list()), 0)
        self.assertEqual(len(self.api_manager.forms.list(cached=False)), 1)

