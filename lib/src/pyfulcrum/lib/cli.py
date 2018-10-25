#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse

from cliff.app import App
from cliff.command import Command
from cliff.commandmanager import CommandManager
from cliff.show import ShowOne

from fulcrum import Fulcrum
from .api import Storage, ApiManager


print_attrs = ('id', 'description', 'name',)


def print_item(obj):
    c = obj.__class__.__name__
    out = [c]
    for pattr in print_attrs:
        vattr = getattr(obj, pattr, None)
        if vattr is not None:
            out.append(vattr)
    print('{}: {}'.format(out[0], ' '.join(out[1:])))


class PyFulcrumApp(App):
    
    description = "PyFulcrum access from cli"
    version = '0.0.1'

    def __init__(self):
        super().__init__(description = self.description,
                         version = self.version,
                         command_manager = CommandManager('pyfulcrum.lib.cli'))

    def build_option_parser(self, description, version, argparse_kwargs=None):
        parser = super().build_option_parser(description, version, argparse_kwargs=argparse_kwargs)
        parser.add_argument('--dburl', type=str, nargs=1, required=True, help="database connection url")
        parser.add_argument('--apikey', type=str, nargs=1, required=True, help="Fulcrum API key")
        parser.add_argument('--storage', type=str, nargs=1, required=True, help="Storage directory root")
        return parser


    def initialize_app(self, argv):
        commands = [List, Get]

        for command in commands:
            self.command_manager.add_command(command.__name__.lower(), command)
        

        #def __init__(self, db, client, storage_cfg):
        opts = self.options
        client = Fulcrum(key=opts.apikey[0])

        self.api_manager = ApiManager(opts.dburl[0], client, {'root_dir': opts.storage[0]})


class List(Command):

    def is_allowed_resource(self, value):
        allowed_values = self.app.api_manager.manager_names
        if value not in allowed_values:
            raise ValueError("Value {} not in allowed resource names".format(value))
        return value
    
    @staticmethod
    def is_urlparam(value):
        if len(value.split('=')) == 2:
            return value.split('=')
        raise ValueError("Cannot use {} as url arg".format(value))


    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument('resource',
                            type=self.is_allowed_resource,
                            nargs=1,
                            help="Name of resource to list (projects, forms, records, values, media)")
        parser.add_argument('--urlparams',
                            type=self.is_urlparam,
                            required=False,
                            nargs='+',
                            help="list of name=value pairs of url params to pass to list")
        parser.add_argument('--ignore-existing',
                            dest='ignore_existing',
                            action='store_true',
                            default=False,
                            required=False,
                            help="Should app fetch only data that are not in local database")
        parser.add_argument('--cached',
                            dest='cached',
                            action='store_true',
                            default=False,
                            required=False,
                            help="Should app fetch data from live API")
        return parser

    def take_action(self, parsed_args):
        api = self.app.api_manager
        mgr = api.get_manager(parsed_args.resource[0])
        url_params = {}
        for un, uv in (parsed_args.urlparams or []):
            url_params[un] = uv
        items = mgr.list(cached=parsed_args.cached,
                         generator=True,
                         ignore_existing=parsed_args.ignore_existing,
                         url_params=url_params)
        for item in items:
            print_item(item)
            if not parsed_args.cached:
                api.flush()
        

class Get(Command):

    def is_allowed_resource(self, value):
        allowed_values = self.app.api_manager.manager_names
        if value not in allowed_values:
            raise ValueError("Value {} not in allowed resource names".format(value))
        return value
        
    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument('resource',
                            type=self.is_allowed_resource,
                            nargs=1,
                            help="Name of resource to get (projects, forms, records, values, media)")

        parser.add_argument('id',
                            type=str,
                            nargs=1,
                            help="ID of resource to get")

        parser.add_argument('--cached',
                            dest='cached',
                            action='store_true',
                            default=False,
                            help="Should app fetch data from live API")
        return parser

    def take_action(self, parsed_args):
        api = self.app.api_manager
        mgr = api.get_manager(parsed_args.resource[0])
        obj_id = parsed_args.id[0]
        item = mgr.get(obj_id, cached=parsed_args.cached)
        print_item(item)
        api.flush()


def main():
    app = PyFulcrumApp()
    return app.run(sys.argv[1:])


if __name__ == '__main__':
    main()