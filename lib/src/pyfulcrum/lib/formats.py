#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
from shapely import wkb
from osgeo import ogr 
from io import StringIO
ogr.UseExceptions()

print_attrs = ('id', 'status', 'name', 'media_type', 'content_type', 'form_id', 'record_id', 'records_count', 'values_processed')


def print_item(obj, storage, output=None):
    if output is None:
        output = sys.stdout

    c = obj.__class__.__name__
    out = [c]
    for pattr in print_attrs:
        vattr = getattr(obj, pattr, None)
        if vattr is not None:
            out.append('{}={}'.format(pattr, vattr))
    print('{}: {}'.format(out[0], ' '.join(out[1:])), file=output)
    if getattr(obj, 'get_paths', None):
        for p, k in obj.get_paths(storage).items():
            print(' size {}: {}'.format(p, k['path']), file=output)

    if getattr(obj, 'get_values', None):
        for key, val in obj.get_values(storage).items():
            print( ' field {} {}: {}'.format(key, val['type'], val['description'] or val['label']), file=output)
            if val['media']:
                for mval in val['media']:
                    if mval.get('caption'):
                        print('  {} (caption: {}):\n   {}'.format(mval['id'],
                                                mval['caption'],
                                                mval['paths'].get('original')), file=output)

                    else:
                        print('  {}:\n   {}'.format(mval['id'],
                                                mval['paths'].get('original')), file=output)
            else:
                print('   value: {}'.format(val['value']), file=output)

def json_item(obj, storage):
    c = obj.__class__.__name__
    out = {'class': c}
    for pattr in print_attrs:
        vattr = getattr(obj, pattr, None)
        if vattr is not None:
            out[pattr] = vattr
    if getattr(obj, 'get_paths', None):
        out['paths'] = obj.get_paths(storage)

    if getattr(obj, 'get_values', None):
        out['values'] = obj.get_values(storage)
    return out


def geojson_item(obj, storage):
    if getattr(obj, 'point', None) is None:
        return
    geom = ogr.CreateGeometryFromWkb(obj.point.data.tobytes())
    out = {'type': 'Feature',
           'geometry': json.loads(geom.ExportToJson()),
           'properties': obj.get_values(storage) if hasattr(obj, 'get_values') else obj.payload}
    return out


def format_str(items, storage, multiple=False):
    out = []
    if not multiple:
        items = [items]
    for item in items:
        output = StringIO()
        print_item(item, storage, output)
        out.append(output.getvalue())
    if not multiple:
        return out[0]
    return '\n'.join(out)


def format_json(items, storage, multiple=False):
    out = []
    if not multiple:
        items = [items]

    for item in items:
        out.append(json_item(item, storage))
    if not multiple:
        return json.dumps(out[0])
    return json.dumps(out)


def format_raw(items, storage, multiple=False):
    out = []
    if not multiple:
        items = [items]

    for item in items:
        out.append(item.payload)
    if not multiple:
        return json.dumps(out[0])
    return json.dumps(out)


def format_geojson(items, storage, multiple=False):
    out = []
    if not multiple:
        items = [items]
    for item in items:
        val = geojson_item(item, storage)
        if val is not None:
            out.append(val)
    if not multiple:
        return json.dumps(out[0])
    return json.dumps({'type': 'FeatureCollection', 'features': out})


FORMATS = {'str': format_str,
           'json': format_json,
           'geojson': format_geojson,
           'raw': format_raw}
