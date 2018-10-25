#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os


class Storage(object):
    def __init__(self, root_dir, url_base=None):
        self.root_dir = os.path.abspath(root_dir)
        self.url_base = url_base
        self.initialize_storage(self.root_dir)

    def initialize_storage(self, dir_name):
        dir_name = os.path.abspath(dir_name)
        os.makedirs(dir_name, exist_ok=True)
        if not os.access(dir_name, os.R_OK|os.W_OK):
            raise ValueError("Path {} is not writable".format(dir_name))

    def get_url(self, form_id, record_id, media_type, size):
        if self.url_base:
            common = self.get_common_path(form_id, record_id, media_type, size)
            return os.path.join(self.url_base, common)

    def get_path(self, form_id, record_id, media_type, size):
        common = self.get_common_path(form_id, record_id, media_type, size)
        return os.path.join(self.root_dir, common)

    def get_common_path(self, form_id, record_id, media_type, size):
        return os.path.join(form_id, record_id, '{}_{}'.format(media_type, size))

    def save(self, fh, form_id, record_id, media_type, size):
        path = self.get_path(form_id, record_id, media_type, size)
        self.initialize_storage(os.path.dirname(path))

        with open(path, 'wb') as f:
            f.write(fh.read())
        return path
