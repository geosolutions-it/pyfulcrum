#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import tempfile
import zipfile
import csv
from functools import wraps
from shapely import wkb
from osgeo import ogr, osr
from io import StringIO
ogr.UseExceptions()

print_attrs = ('id', 'status', 'name', 'media_type', 'content_type', 'form_id', 'record_id', 'records_count', 'values_processed')


def formatter(allowed_classes=None):
    """
    Decorator for formatter callable - provides
    common checks and returns if item passed is
    empty value.

    @param allowed_classes list of allowed class names
        that format supports. If ommited, all classes
        can be used

    usage:

    @formatter()
    def format_xyz(items, storage, multiple):
        ...

    or

    @formatter(['Record', 'Media'])
    def format_xyx(items, storage, multiple):
        ...

    or


    @formatter('Record')
    def format_xyx(items, storage, multiple):
        ...

    """
    def _formatter(f):
        @wraps(f)    
        def _wrap(items, storage, multiple=False):
            if not items:
                if multiple:
                    return []
                return
            if not multiple:
                items = [items]
            if allowed_classes:
                cls_name = items[0].__class__.__name__
                if isinstance(allowed_classes, list):
                    if cls_name not in allowed_classes:
                        raise TypeError("Cannot use class {} with {}"
                                        .format(cls_name, f.__name__))
                else:
                    if cls_name != allowed_classes:
                        raise TypeError("Cannot use class {} with {}"
                                        .format(cls_name, f.__name__))
                        
            return f(items, storage, multiple=multiple)
        return _wrap
    return _formatter


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
           'id': obj.id,
           'geometry': json.loads(geom.ExportToJson()),
           'properties': obj.get_values(storage) if hasattr(obj, 'get_values') else obj.payload}
    out['properties']['id'] = obj.id
    return out

@formatter()
def format_str(items, storage, multiple=False):
    out = []
    for item in items:
        output = StringIO()
        print_item(item, storage, output)
        out.append(output.getvalue())
    if not multiple:
        return out[0]
    return '\n'.join(out)


@formatter()
def format_json(items, storage, multiple=False):
    out = []
    for item in items:
        out.append(json_item(item, storage))
    if not multiple:
        return json.dumps(out[0])
    return json.dumps(out)


@formatter()
def format_raw(items, storage, multiple=False):
    out = []
    for item in items:
        out.append(item.payload)
    if not multiple:
        return json.dumps(out[0])
    return json.dumps(out)


@formatter('Record')
def format_geojson(items, storage, multiple=False):
    out = []
    for item in items:
        val = geojson_item(item, storage)
        if val is not None:
            out.append(val)
    if not multiple:
        return json.dumps(out[0])
    return json.dumps({'type': 'FeatureCollection', 'features': out})

@formatter()
def format_csv(items, storage, multiple=False):
    out = StringIO()
    w = csv.writer(out, quoting=csv.QUOTE_NONNUMERIC)
    header = ['id']
    item_row = items[0]
    for fname in item_row.payload.keys():
        # id was already added
        if fname == 'id': 
            continue

        # form values is a dictionary, we need to extract each field
        if fname == 'form_values':
            for fname, value in item_row.payload['form_values'].items():
                header.append('field.{}'.format(fname))
        else:
            header.append(fname)
    header = header[:1] + list(sorted(header[1:]))
    w.writerow(header)

    for item in items:
        row = [item.id]
        payload = item.payload
        for k in header[1:]:
            if k.startswith('field.'):
                fname = k[6:]
                row.append(payload['form_values'][fname])
            else:
                row.append(payload[k])
        w.writerow(row)
    return out.getvalue()


@formatter('Record')
def format_shapefile(items, storage, multiple=False):
    """
    Output to shapefile as zip
    """

    return _export_ogr(items, storage, multiple,
                       driver='ESRI Shapefile',
                       extension='shp',
                       use_zip=True)


@formatter('Record')
def format_kml(items, storage, multiple=False):
    """
    Output to shapefile as zip
    """

    return _export_ogr(items, storage, multiple,
                       driver='KML',
                       extension='kml',
                       use_zip=False)

def _export_ogr(items, storage, multiple=False, driver=None, extension=None, use_zip=False):
    item_class = items[0].__class__.__name__
    item_row = items[0]
    # we don't want to process entries without geometry
    if not hasattr(item_row, 'point'):
        return

    # need to extract field names from first item in list
    item_defs = [('id', ogr.FieldDefn('id', ogr.OFTString), 0,)]
   
    item_idx = 0
    for fname in item_row.payload.keys():
        # id was already added
        if fname == 'id': 
            continue
        # form values is a dictionary, we need to extract each field
        if fname == 'form_values':
            for fname, value in item_row.payload['form_values'].items():
                item_defs.append(('field.{}'.format(fname), ogr.FieldDefn('f_{}'.format(fname), ogr.OFTString), item_idx,))
                item_idx += 1
        else:
            # warning: SHP has silly limitation on field name, it will
            # truncate longer names. Better to use GeoJSON instead
            item_defs.append((fname, ogr.FieldDefn(fname, ogr.OFTString), item_idx,))
        item_idx += 1
        
    basename = '{}s'.format(item_class.lower())
    outfile = '{}.{}'.format(basename, extension)
    zfile = '{}.zip'.format(outfile)

    drv = ogr.GetDriverByName(driver)
    with tempfile.TemporaryDirectory() as tmpdirname:
        full_path = os.path.join(tmpdirname, outfile)
        data = drv.CreateDataSource(full_path)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        layer = data.CreateLayer(basename, srs, ogr.wkbPoint)

        # create layer definitions from fields from above
        for fname, fdef, fidx in item_defs:
            layer.CreateField(fdef)
        ldef = layer.GetLayerDefn()
        for item in items:
            feat = ogr.Feature(layer.GetLayerDefn())
            # populate properties
            for fname, fdef, fidx in item_defs:
                if fname == 'id':
                    value = item.id
                # form value, need to serialize to json
                # warning - SHP has silly 256 char limitation for VALUE
                # that means some fields may be truncated
                elif fname.startswith('field.'):
                    value = json.dumps(item.payload['form_values'].get(fname[len('field.'):]))
                else:
                    value = item.payload[fname]
                # definition expects string here
                if isinstance(value, (list, dict,)):
                    value = json.dumps(value)
                feat.SetField(fidx, value)
            point = item.point.data.tobytes()
            geom = ogr.CreateGeometryFromWkb(point)
            feat.SetGeometry(geom)
            layer.CreateFeature(feat)
        data.Destroy()

        if use_zip:

            files = os.listdir(tmpdirname)
            zfile = os.path.join(tmpdirname, zfile)

            with zipfile.ZipFile(zfile, mode='w') as zf:
                for fname in files:
                    # no subpath for archive names by using arcname
                    zf.write(os.path.join(tmpdirname, fname), arcname='/{}'.format(fname))
            
            with open(zfile, 'rb') as zf:
                return zf.read()
        else:
            with open(full_path, 'rb') as f:
                return f.read()

FORMATS = {'str': format_str,
           'json': format_json,
           'geojson': format_geojson,
           'shapefile': format_shapefile,
           'kml': format_kml,
           'csv': format_csv,
           'raw': format_raw}
