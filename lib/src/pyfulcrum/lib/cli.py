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
from .formats import FORMATS


AVAILABLE_FORMATS = list(sorted(FORMATS.keys()))

def valid_format(value):
    if value in AVAILABLE_FORMATS:
        return value
    raise ValueError("Invalid format: {}".format(value))


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
        parser.add_argument('--urlbase', type=str, nargs=1, required=False, default=(None,),
                            help="Web root for storage")
        parser.add_argument('--format', type=valid_format, nargs=1, required=False, default=('json',),
                            help="Return format (default: json, "
                                 "available: {}). Mind that spatial-aware formatters accept "
                                 "only record objects.".format(','.join(AVAILABLE_FORMATS))),
        parser.add_argument('--output', type=str, nargs=1, required=False, default=tuple(),
                            help="Name of output file, standard output as default")
        return parser


    def initialize_app(self, argv):
        commands = [List, Get, Delete]

        for command in commands:
            self.command_manager.add_command(command.__name__.lower(), command)
        

        #def __init__(self, db, client, storage_cfg):
        opts = self.options
        client = Fulcrum(key=opts.apikey[0])

        self.api_manager = ApiManager(opts.dburl[0], client, {'root_dir': opts.storage[0],
                                                              'url_base': opts.urlbase[0]})


class _BaseCommand(Command):

    def is_allowed_resource(self, value):
        allowed_values = self.app.api_manager.manager_names
        if value not in allowed_values:
            raise ValueError("Value {} not in allowed resource names".format(value))
        return value

    def write_output(self, output):
        output_f = self.app.options.output[0] if self.app.options.output else None
        if output_f:
            with open(output_f, 'wb+') as f:
                f.write(output)
        else:
            print(output)

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
        parser.add_argument('--cached',
                            dest='cached',
                            action='store_true',
                            default=False,
                            required=False,
                            help="Should app fetch data from live API")
        return parser


class List(_BaseCommand):
    """
    List resources
    """

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
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
        return parser

    def take_action(self, parsed_args):
        format = self.app.options.format[0]
        with self.app.api_manager as api:
            mgr = api.get_manager(parsed_args.resource[0])
            url_params = {}
            for un, uv in (parsed_args.urlparams or []):
                url_params[un] = uv
            items = mgr.list(cached=parsed_args.cached,
                             generator=True,
                             ignore_existing=parsed_args.ignore_existing,
                             url_params=url_params)
            output = api.as_format(format, items, multiple=True)
            self.write_output(output)

class Get(_BaseCommand):
    """
    Shows single resource
    """
    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument('id',
                            type=str,
                            nargs=1,
                            help="ID of resource to get")
        return parser

    def take_action(self, parsed_args):
        format = self.app.options.format[0]
        with self.app.api_manager as api:
            mgr = api.get_manager(parsed_args.resource[0])
            obj_id = parsed_args.id[0]
            item = mgr.get(obj_id, cached=parsed_args.cached)
            output = api.as_format(format, item)
            self.write_output(output)


class Delete(_BaseCommand):
    """
    Removes resource
    """
    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument('id',
                            type=str,
                            nargs=1,
                            help="ID of resource to get")
        return parser

    def take_action(self, parsed_args):
        format = self.app.options.format[0]
        with self.app.api_manager as api:
            mgr = api.get_manager(parsed_args.resource[0])
            obj_id = parsed_args.id[0]
            item = mgr.delete(obj_id)
            output = api.as_format(format, item)
            self.write_output(output)


def main():
    app = PyFulcrumApp()
    return app.run(sys.argv[1:])


if __name__ == '__main__':
    main()
