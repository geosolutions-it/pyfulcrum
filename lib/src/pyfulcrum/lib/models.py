#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from datetime import datetime
from sqlalchemy import (Column, Integer, String,
                        DateTime, Numeric, ForeignKey,
                        JSON, Enum, Boolean)
from sqlalchemy.orm import relationship
from sqlalchemy.schema import MetaData
from sqlalchemy.orm.session import sessionmaker

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from geoalchemy2 import Geometry

from urllib.request import urlopen

md = MetaData()
Session = sessionmaker()

Base = declarative_base(metadata=md)

# "created_at": "2015-04-16T13:20:10Z",
DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


class BaseResource(Base):
    """
    Base class for data objects. This contains common tables
    and methods.
    """
    # list of field->column mappings (if it's a string, both
    # names are euqal. alternatively you can provide tuple
    # with source, dest names, i.e. ('id', 'media_key',))
    MAPPED_COLUMNS = ('id', 'created_at', 'updated_at',)

    __abstract__ = True

    # judging from example values this is probably uuid,
    # but api schema says string
    # also, in media resources it's media_key
    id = Column(String, primary_key=True)
    created_at = Column(DateTime(timezone=True),
                        nullable=False,
                        server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        nullable=False,
                        server_default=func.now(),
                        onupdate=func.now())
    fetched_at = Column(DateTime(timezone=True),
                        nullable=True,
                        server_default=func.now(),
                        onupdate=func.now())
    # raw json received for object
    payload = Column(JSON, nullable=True)
    removed = Column(Boolean, nullable=False, default=False, index=True)

    def __str__(self):
        return u'{}({})'.format(self.__class__.__name__, self.id)

    __repr__ = __str__

    @classmethod
    def get_q_params(self, *args, **kwargs):
        """
        Subclass should override this to provide
        mapping between url params and query filter
        """
        return []

    @classmethod
    def get(cls, id, session):
        s = session 
        return s.query(cls).filter(cls.id == id).first()

    @classmethod
    def exists(cls, id, session):
        s = session
        return s.query(cls.query.filter(cls.id == id).exists()).scalar()

    @classmethod
    def _post_payload(cls, instance, payload, session, client, storage):
        pass

    @classmethod
    def _pre_payload(cls, payload, session, client, storage):
        return payload

    @classmethod
    def from_payload(cls, payload, session, client, storage):
        s = session

        # hook for preprocessing class-specific payload
        payload = cls._pre_payload(payload, s, client, storage)

        id = payload['id']
        existing = cls.get(id, session=s)
        if not existing:
            existing = cls(id=id)
        for m in cls.MAPPED_COLUMNS:
            if isinstance(m, (list, tuple,)):
                msrc, mdest = m
            else:
                msrc = mdest = m
            setattr(existing, mdest, payload[msrc])

        # hook for subclasses
        # also, should clean payload
        cls._post_payload(existing, payload, s, client, storage)

        existing.payload = payload
        s.add(existing)
        s.flush()
        return existing


class Project(BaseResource):
    __tablename__ = 'fulcrum_project'
    name = Column(String, index=True)
    description = Column(String(1024))
    MAPPED_COLUMNS = BaseResource.MAPPED_COLUMNS + ('name', 'description',)


class Form(BaseResource):
    __tablename__ = 'fulcrum_form'
    name = Column(String, index=True)
    description = Column(String(1024))
    fields = Column(JSON, nullable=False)
    MAPPED_COLUMNS = (BaseResource.MAPPED_COLUMNS +
                      ('name', 'description', ('elements', 'fields',),)
                      )

    @property
    def records_count(self):
        return len(self.records)

    @classmethod
    def _post_payload(cls, instance, payload, session, client, storage):
        # here we should process fields
        # but first, we need to add this form to db
        session.add(instance)
        session.flush()
        for f in payload['elements']:
            f['form_id'] = instance.id
            f['id'] = f['key']
            Field.from_payload(f, session, client, storage)
        return

    @classmethod
    def get_q_params(cls, url_params, *args, **kwargs):
        if url_params.get('form_id'):
            return [cls.id == url_params['form_id']]

# list of available field types from api docs
# see https://developer.fulcrumapp.com/endpoints/\
# forms/#form-element-properties-all-field-types
FIELD_TYPES = ("TextField", "YesNoField", "Label",
               "Section", "ChoiceField", "ClassificationField",
               "PhotoField", "VideoField", "AudioField",
               "BarcodeField", "DateTimeField", "TimeField",
               "Repeatable", "AddressField",
               "SignatureField", "HyperlinkField",
               "CalculatedField", "RecordLinkField",)

FieldTypeEnum = Enum(*FIELD_TYPES, name='field_types')


class Field(BaseResource):
    __tablename__ = 'fulcrum_field'
    form_id = Column(String, ForeignKey('fulcrum_form.id'), nullable=False)
    label = Column(String, nullable=False, index=True)
    data_name = Column(String, nullable=False, index=True)
    description = Column(String)
    required = Column(Boolean, nullable=False)
    disabled = Column(Boolean, nullable=False)
    hidden = Column(Boolean, nullable=False)
    type = Column(FieldTypeEnum, nullable=False)
    form = relationship(Form, backref="fields_list")
    MAPPED_COLUMNS = (BaseResource.MAPPED_COLUMNS +
                      ('label', 'data_name', 'description',
                       'required', 'disabled', 'hidden',
                       'type', 'form_id',)
                      )

    def __str__(self):
        return 'Field({}, label={}, type={}, description={})'.format(self.id, self.label, self.type, self.description)
    
    @classmethod
    def _pre_payload(cls, payload, session, client, storage):
        payload['created_at'] = payload['updated_at'] =\
         datetime.utcnow().strftime(DATE_FORMAT)
        return payload

    @classmethod
    def _post_payload(cls, instance, payload, session, client, storage):
        # cleanup payload for saving
        payload.pop('form_id', None)
        payload.pop('id', None)
        payload.pop('created_at', None)
        payload.pop('updated_at', None)

    @property
    def media_key(self):
        if self.type in ('SignatureField', 'AudioField', 'PhotoField', 'VideoField',):
            return '{}_id'.format(self.type.lower()[:-len('field')])


class Record(BaseResource):
    __tablename__ = 'fulcrum_record'
    form_id = Column(String, ForeignKey('fulcrum_form.id'), nullable=False)
    project_id = Column(String,
                        ForeignKey('fulcrum_project.id'),
                        nullable=True)
    point = Column(Geometry('POINT'), nullable=True, index=True)
    altitude = Column(Integer, nullable=True)
    speed = Column(Numeric, nullable=True)
    course = Column(Numeric, nullable=True)
    values = Column(JSON, nullable=True)
    status = Column(String, nullable=True, index=True)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=True)
    assigned_to = Column(String, nullable=True)
    form = relationship(Form, backref="records")
    project = relationship(Project, backref="records")

    MAPPED_COLUMNS = (BaseResource.MAPPED_COLUMNS +
                      ('form_id', 'project_id', 'point',
                       'altitude', 'speed', 'course',
                       'values', 'status', 'created_by',
                       'updated_by', 'assigned_to',)
                      )
    
    def get_values(self, storage):
        media = {}
        for m in self.media_list:
            try:
                media[m.id].append(m)
            except KeyError:
                media[m.id] = [m]
        out = {}
        for val in self.values_list:
            fval = val.get_value(storage)
            out[fval['label']] = fval
        return out

    @classmethod
    def _pre_payload(cls, payload, session, client, storage):
        f = payload
        point = None
        if f.get('latitude') and f.get('longitude'):
            point = 'POINT({latitude} {longitude})'.format(latitude=f['latitude'],
                                                           longitude=f['longitude'])
        f['point'] = point
        f['values'] = f['form_values']
        return f

    @classmethod
    def _post_payload(cls, instance, payload, session, client, storage):
        session.add(instance)
        session.flush()

        for field_id, field_value in payload['form_values'].items():
            fdef = Field.get(field_id, session=session)
            if fdef is None:
                raise ValueError("There's no field definition for id {}".format(field_id))
            f = {}
            f['type'] = fdef.type
            f['record_id'] = instance.id
            f['value'] = field_value
            f['meta'] = {'key': field_id,
                         'value': field_value}
            f['field_id'] = field_id
            f['created_at'] = instance.created_at
            f['updated_at'] = instance.updated_at
            f['id'] = '{}_{}'.format(instance.id, field_id)
            Value.from_payload(f, session, client, storage)
            
       # cleanup payload for saving
        payload.pop('point', None)
        payload.pop('values', None)

    @classmethod
    def get_q_params(cls, url_params, *args, **kwargs):
        if url_params.get('form_id'):
            return [cls.form_id == url_params['form_id']]


class Value(BaseResource):
    __tablename__ = 'fulcrum_value'

    field_id = Column(String,
                      ForeignKey('fulcrum_field.id'),
                      nullable=False)
    record_id = Column(String,
                       ForeignKey('fulcrum_record.id'),
                       nullable=False)
    # value can be any type (dict, list, number, string..)
    value = Column(JSON, nullable=False, default='')
    type = Column(FieldTypeEnum, nullable=False, index=True)
    meta = Column(JSON, nullable=False)
    field = relationship(Field, backref='values_list')
    record = relationship(Record, backref='values_list')


    MAPPED_COLUMNS = (BaseResource.MAPPED_COLUMNS +
                      ('field_id', 'record_id',
                       'value', 'meta', 'type',))

    @classmethod
    def _post_payload(cls, instance, payload, session, client, storage):
        pkeys = payload.keys()
        for k in list(pkeys):
            if k == 'meta':
                continue
            payload.pop(k)


    def get_value(self, storage):
        field = self.field
        out = {'key': self.field_id,
               'description': field.description,
               'label': field.label,
               'type': field.type,
               'value': self.value,
               'media': [],
               }
        # name of key in values list with media id
        media_key = field.media_key
        if media_key:
            media = dict((m.id, m) for m in self.record.media_list)
            # iterate over items in value
            values = self.value
            if isinstance(self.value, dict):
                values = [self.value]
                
            for media_item in values:
                mkey = media_item[media_key]
                caption = media_item.get('caption')
                m = media[mkey]
                if m:
                    out['media'].append({'id': m.id,
                                         'caption': caption,
                                         'type': m.media_type,
                                         'paths': m.get_paths(storage)})
        return out

class Media(BaseResource):
    MEDIA_PHOTO = 'photo'
    MEDIA_AUDIO = 'audio'
    MEDIA_VIDEO = 'video'
    MEDIA_SIGNATURE = 'signature'
    MEDIA_TYPES = (MEDIA_PHOTO, MEDIA_AUDIO, MEDIA_VIDEO, MEDIA_SIGNATURE,)
    KEY_COLUMN = 'access_key'

    __tablename__ = 'fulcrum_media'
    # access_key = Column(String, nullable=False, unique=True)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=True)
    point = Column(Geometry('POINT'), nullable=True)
    record_id = Column(String,
                       ForeignKey('fulcrum_record.id'),
                       nullable=False)
    form_id = Column(String, ForeignKey('fulcrum_form.id'), nullable=False)
    file_size = Column(Integer, nullable=False)
    content_type = Column(String, nullable=False)
    track = Column(Geometry('LINESTRING'), nullable=True)
    media_type = Column(Enum(*MEDIA_TYPES, name='media_types'), nullable=False, index=True)
    form = relationship(Form, backref='media_list')
    record = relationship(Record, backref='media_list')

    MAPPED_COLUMNS = (BaseResource.MAPPED_COLUMNS +
                      ('created_by', 'updated_by', 'point',
                       'record_id', 'form_id',
                       'file_size', 'content_type',
                       'media_type'))

    SIZES_PHOTO = ('large', 'thumbnail', 'original',)
    SIZES_SIGNATURE = SIZES_PHOTO
    SIZES_VIDEO = ('thumbnail_small', 'thumbnail_medium',
                   'thumbnail_large', 'thumbnail_huge',
                   'thumbnail_small_square',
                   'thumbnail_medium_square',
                   'thumbnail_large_square',
                   'thumbnail_huge_square',
                   'small', 'medium',
                   'original',)
    SIZES_AUDIO = ('small', 'medium', 'original',)
    SIZES_ALL = tuple(set(SIZES_PHOTO + SIZES_SIGNATURE + SIZES_VIDEO + SIZES_AUDIO))
    SIZES = {'photo': SIZES_PHOTO,
             'audio': SIZES_AUDIO,
             'signature': SIZES_SIGNATURE,
             'video': SIZES_VIDEO}

    @classmethod
    def _pre_payload(cls, payload, session, client, storage):
        f = payload
        f['id'] = f['access_key']
        point = None
        if f.get('latitude') and f.get('longitude'):
            point = 'POINT({latitude} {longitude})'.format(latitude=f['latitude'],
                                                           longitude=f['longitude'])
        f['point'] = point
            
        return payload

    def get_path(self, storage, size):
        return storage.get_path(self.form_id,
                                self.record_id,
                                self.media_type,
                                size)

    def get_common_path(self, storage, size):
        return storage.get_common_path(self.form_id,
                                       self.record_id,
                                       self.media_type,
                                       size)

    def get_url(self, storage, size):
        return storage.get_url(self.form_id,
                               self.record_id,
                               self.media_type,
                               size)

    def get_paths(self, storage):
        out = {}
        for s in self.SIZES[self.media_type]:
            out[s] = {'path': self.get_path(storage, s),
                      'url': self.get_url(storage, s)}
        return out

    def save_to_storage(self, storage, fhandle, size):
        storage.save(fhandle, self.form_id, self.record_id, self.media_type, size)

    @classmethod
    def _post_payload(cls, instance, payload, session, client, storage):
        # handle storage

        media_type = payload['media_type']
        sizes = cls.SIZES[media_type]
        for s in sizes:
            media_url = payload.get(s)
            if media_url is None:
                continue
            u = urlopen(media_url)
            instance.save_to_storage(storage, u, s)

        return payload


__all__ = ['Media', 'Value', 'Record', 'Field',
           'Project', 'Form', 'Base', 'Session']
