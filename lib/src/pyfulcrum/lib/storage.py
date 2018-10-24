#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os


class Storage(object):
    def __init__(self, root_dir, url_base=None):
        self.root_dir = root_dir
        self.url_base = url_base
        self.initialize_storage()

    def initialize_storage(self):
        os.makedirs(self.root_dir, exist_ok=True)
        if not os.access(self.root_dir, os.R_OK|os.W_OK):
            raise ValueError("Path {} is not writable".format(self.root_dir))

    def get_url(self, form_id, record_id, field_id, media_type, size):
        if self.url_base:
            common = self.get_common_path(form_id, record_id, field_id, media_type, size)
            return os.path.join(self.url_base, common)

    def get_path(self, form_id, record_id, field_id, media_type, size):
        common = self.get_common_path(form_id, record_id, field_id, media_type, size)
        return os.path.join(self.root_dir, common)

    def get_common_path(self, form_id, record_id, field_id, media_type, size):
        return os.path.join(form_id, record_id, field_id, '{}_{}_{}'.format(field_id, media_type, size))

    def save(self, fh, form_id, record_id, field_id, media_type, size):
        path = self.get_path(form_id, record_id, field_id, media_type, size)
        with open(path, 'wb') as f:
            f.write(fh.read())
        return path
