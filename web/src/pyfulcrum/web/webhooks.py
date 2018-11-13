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
    out = fulcrum_call(name, res_name, res_action, res_id, payload)
    return Response(out or 'ok')

def fulcrum_call(config_name, res_name, res_action, res_id, payload):
    # any intermediate actions here
    try:
        return _handle_webhook(config_name, res_name, res_action, res_id, payload)
    except HTTPException:
        raise
    except Exception as err:
        log.warning("Cannot process event %s.%s for id %s in %s webhook: %s", res_name, res_action, res_id, config_name, err, exc_info=err)
        return str(err)

def _parse_objects_list(value):
    """
    returns mapping of resource -> list of ids
    from a string like 'records:id1,id2;forms:id1,id2'
    """
    if not value:
        return {}
    out = {}
    for line in value.split(';'):
        try:
            rname, ids = line.split(':', 1)
        except ValueError:
            continue
        out[rname] = ids.split(',')
    return out



def _handle_webhook(config_name, res_name, res_action, res_id, payload):
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
    
    include_objects = _parse_objects_list(config.pop('include_objects', None))
    exclude_objects = _parse_objects_list(config.pop('exclude_objects', None))
    pdata = payload.get('data') or {}

    check_objects = [(res_name, res_id,)]
    if pdata.get('form_id'):
        check_objects.append(('form', pdata['form_id'],))
    if pdata.get('record_id'):
        check_objects.append(('record', pdata['record_id'],))

    # test parent objects as well, so if we exclude form,
    # we should also exclude all records/media for that form
    for check_type, check_id in check_objects:

        include_obj = include_objects.get(check_type) or []
        exclude_obj = exclude_objects.get(check_type) or []

        if include_obj and check_id not in include_obj:
            log.warning("Object %s not in include list %s for %s", check_id, include_obj, check_type)
            return 'whitelisted'

        elif exclude_obj and check_id in exclude_obj:
            log.warning("Object %s in exclude list %s for %s", check_id, exclude_obj, check_type)
            return 'blacklisted'

    api_manager = ApiManager(**config)
    with api_manager:

            
        if res_name != 'audio':
            res_name = '{}s'.format(res_name)

        mgr = api_manager.get_manager(res_name)
        if res_action == 'delete':
            mgr.remove(res_id)
        else:
            mgr.get(res_id, cached=False)
