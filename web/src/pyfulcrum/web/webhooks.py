#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from werkzeug.exceptions import HTTPException
from flask import Blueprint, abort, current_app, Response, request
from pyfulcrum.lib.api import ApiManager


log = logging.getLogger(__name__)
webhooks = Blueprint('pyfulcrum.web.webhooks', __name__)

@webhooks.route('/webhook/<name>/', methods=['POST'])
def webhook_in(name):
    """
    view for handling incoming Fulcrum webhook.
    """
    if not request.data:
        abort(Response('empty payload', status=200))
    payload = request.json
    if not payload:
        abort(Response('empty json payload', status=200))
    ptype = payload.get('type') or 'invalid.type'
    if not (ptype.startswith('form.') or ptype.startswith('record.')):
        # we don't consider this as an error, because fulcrum will repeat it otherwise
        return Response('cannot handle {} event type'.format(ptype))
    
    try:
        res_name, res_action = ptype.split('.')
    except IndexError:
        return Response('cannot handle {} event type'.format(ptype))

    res_id = (payload.get('data') or {}).get('id')
    if not res_id:
        return Response('cannot handle {} event type with empty object id'.format(ptype))
        

    # this can be called outside web process, with task queue
    out = fulcrum_call(name, res_name, res_action, res_id)
    return Response('ok')

def fulcrum_call(config_name, res_name, res_action, res_id):
    # any intermediate actions here
    try:
        return _handle_webhook(config_name, res_name, res_action, res_id)
    except HTTPException:
        raise
    except Exception as err:
        log.warning("Cannot process event %s.%s for id %s in %s webhook: %s", res_name, res_action, res_id, config_name, err, exc_info=err)

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
    config = current_app.config.get_namespace('WEBHOOK_{}_'.format(config_name.upper()))
    if not config:
        abort(Response('webhook {} configuration not found'.format(config_name), status=404))
        
    api_manager = ApiManager(**config)
    with api_manager:
        if res_name != 'audio':
            res_name = '{}s'.format(res_name)

        mgr = api_manager.get_manager(res_name)
        if res_action == 'delete':
            mgr.remove(res_id)
        else:
            mgr.get(res_id, cached=False)
