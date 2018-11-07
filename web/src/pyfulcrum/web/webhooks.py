#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Blueprint, abort, current_app, Response, request
from pyfulcrum.lib.api import ApiManager


webhooks = Blueprint('pyfulcrum.web.webhooks', __name__)

@webhooks.route('/webhook/<name>/', methods=['POST'])
def webhook_in(name):
    """
    view for handling incoming Fulcrum webhook.

    This view will 
    """
    payload = request.json
    if not payload:
        abort(400)
    ptype = payload['type'];
    if not (ptype.startswith('form.') or ptype.startswith('record.')):
        return Response('cannot handle {} event type'.format(ptype))
    res_name, res_action = ptype.split('.')
    res_id = payload['data']['id']

    # this can be called outside web process, with task queue
    fulcrum_call(name, res_name, res_action, res_id)


def fulcrum_call(config_name, res_name, res_action, res_id):
    # any intermediate actions here
    return _handle_webhook(config_name, res_name, res_action, res_id)

def _handle_webhook(config_name, res_name, res_action, res_id):
    """
    Actual webhook processing

    This will fetch webhook configuration based on name.
    Configuration

    """
    
    # dictionary with webhook ids
    # webhook configuration
    # * db  url
    # * client  api key
    # * storage  path
    whinst = current_app.config.get_namespace('WEBHOOK_{}_'.format(config_name.upper()))
    if not whinst:
        abort(Response('webhook {} configuration not found'.format(config_name), status=404))

    api_manager = ApiManager(**whinst)
    with api_manager:
        if res_name != 'audio':
            res_name = '{}s'.format(res_name)

        mgr = api_manager.get_manager(res_name)
        if res_action == 'delete':
            mgr.delete(res_id)
        else:
            mgr.get(res_id, cached=False)
