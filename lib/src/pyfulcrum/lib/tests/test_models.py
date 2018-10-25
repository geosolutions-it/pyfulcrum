#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from . import BaseTestCase


class ModelsTestCase(BaseTestCase):
    def test_projects(self):
        p = self.api_manager.create_project(id='aaa',
                                            name='test proj',
                                            description='test proj')
        self.assertIsNotNone(p)
        self.assertEqual(len(self.api_manager.get_projects()), 1)
        self.assertEqual(len(list(self.api_manager.projects.list())), 1)
        projects = self.api_manager.projects.list(cached=False)
        self.assertEqual(len(list(projects)), 2)

        # generator flag will return iterable which will return live resutls only
        # ommiting ones from db
        projects = self.api_manager.projects.list(cached=False, generator=True)
        self.assertEqual(len(list(projects)), 1)

        projects = self.api_manager.get_projects()
        self.assertEqual(len(projects), 2, projects)

    def test_forms(self):

        self.assertEqual(len(list(self.api_manager.forms.list())), 0)
        self.assertEqual(len(list(self.api_manager.forms.list(cached=False))), 1)

        FIELD_PAYLOAD = json.loads("""
                        {"type": "TextField",
                         "key": "2832",
                         "label": "ID Tag",
                         "description": "Enter the asset tag ID",
                         "required": false,
                         "disabled": false,
                         "hidden": false,
                         "data_name": "id_tag",
                         "default_value": null,
                         "visible_conditions_type": null,
                         "visible_conditions": null,
                         "required_conditions_type": null,
                         "required_conditions": null,
                         "numeric": false,
                         "pattern": null,
                         "pattern_description": null,
                         "min_length": null,
                         "max_length": null
                        }""")
        field = self.api_manager.fields.get('2832')
        self.assertIsNotNone(field)
        self.assertEqual(field.description, FIELD_PAYLOAD['description'])
        self.assertEqual(field.payload, FIELD_PAYLOAD)
        
        form = self.api_manager.forms.get("7a0c3378-b63a-4707-b459-df499698f23c")
        self.assertEqual(len(form.fields_list),5) 
        self.assertEqual(len(form.fields),5) 

    def test_records(self):
        forms = self.api_manager.forms.list(cached=False)
        self.assertEqual(len(list(self.api_manager.records.list())), 0)
        self.assertEqual(len(list(self.api_manager.records.list(cached=False))), 1)

    def test_media(self):
        self.assertEqual(len(list(self.api_manager.forms.list(cached=False))), 1)
        self.assertEqual(len(list(self.api_manager.records.list(cached=False))), 1)
        self.assertEqual(len(list(self.api_manager.photos.list(cached=False))), 1)
        photo = self.api_manager.photos.list()[0]
        
        photo_links = photo.get_paths(self.api_manager.storage)
        expected = ('large', 'thumbnail', 'original',)
        self.assertEqual(set(expected), set(photo_links.keys()))
