#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template, abort, current_app, Response, request
from jinja2 import TemplateNotFound


webhooks = Blueprint('pyfulcrum.web.webhooks', __name__)

@webhooks.route('/webhook/<name>/')
def webhook_in(name):
    # dictionary with webhook ids
    whconfig = current_app.config.get('webhooks')
    if not whconfig:
        abort(Response('webhooks configuration not found', status=404))
    # webhook configuration
    # * api key
    # * database url
    # * storage path
    whinst = whconfig.get(name)
    if not whinst:
        abort(Response('webhook {} configuration not found'.format(name), status=404))

    payload = request.data
    ptype = payload['type'];
    if not (ptype.startswith('form.') or ptype.startswith('record.')):
        return Response('cannot handle {} event type'.format(ptype))
    res_name, res_action = ptype.split('.')
    res_id = payload['data']['id']

    # this can be called outside web process, with task queue
    fulcrum_call(whinst, res_name, res_action, res_id)


def fulcrum_call(config, res_name, res_action, res_id):
    api_manager = ApiManager(**args)
    _handle_webhook(api_manager, res_name, res_action, res_id)

def _handle_webhook(api_manager, res_name, res_action, res_id)
    api_manager = whinst['api_manager']
    mgr = api_manager.get_manager(res_name)
    if res_action == 'delete':
        mgr.delete(res_id)
    else:
        mgr.get(res_id, cached=False)
