#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
from datetime import datetime
from sqlalchemy import (Column, Integer, String,
                        DateTime, Numeric, ForeignKey,
                        JSON, Enum, Boolean,
                        and_)
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
    def get(cls, id, session, if_removed=False):
        """
        Return BaseResource instance with given id or None.

        @param id object pk
        @param session SQLAlchemy session

        """
        s = session
        if if_removed:
            return s.query(cls).filter(cls.id == id).first()
        return s.query(cls).filter(cls.removed==False, cls.id == id).first()

    @classmethod
    def exists(cls, id, session):
        """
        Returns True if there's resource for given id.

        @param id object pk
        @param session SQLAlchemy session
        """
        s = session
        return s.query(cls.query.filter(cls.id == id).exists()).scalar()

    @classmethod
    def _post_payload(cls, instance, payload, session, client, storage):
        """
        Hook to process instance created/updated with .from_payload().
        Payload can be changed in-place, it won't be saved after this point.
        Subclass can override default implementation.

        @param instance existing instance of resource
        @param payload dict with JSON payload from Fulcrum API
        @param session SQLAlchemy session
        @param client Fulcrum API client instance
        @param storage pyfulcrum.lib.storage.Storage instance
        """
        pass

    @classmethod
    def _pre_payload(cls, payload, session, client, storage):
        """
        Hook to process payload before creating/updating instance with
        .from_payload(). Modified payload should be returned from this
        method.
        Subclass can override default implementation.

        @param payload dict with JSON payload from Fulcrum API
        @param session SQLAlchemy session
        @param client Fulcrum API client instance
        @param storage pyfulcrum.lib.storage.Storage instance
        """
        return payload

    @classmethod
    def from_payload(cls, payload, session, client, storage, reset_removed=True):
        """
        Entry point method for creating/updating instances from
        Fulcrum API payload.
        
        Payload will be processed and each field in MAPPED_COLUMNS
        will be populated based on source field.

        Internally, some pre/postprocessing can be done with
        _pre_payload()/_post_payload() methods in subclasses.
        This method should not be overriden by subclass.

        @param payload dict with JSON payload from Fulcrum API
        @param session SQLAlchemy session
        @param client Fulcrum API client instance
        @param storage pyfulcrum.lib.storage.Storage instance
        
        @returns BaseResource instance
        """
        s = session

        # hook for preprocessing class-specific payload
        payload = cls._pre_payload(payload, s, client, storage)

        id = payload['id']
        existing = cls.get(id, session=s, if_removed=True)
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

        if reset_removed:
            for pname in cls.PARENT_ATTRS:
                phandler = getattr(existing, pname, None)
                if phandler and phandler.removed:
                    raise ValueError("Cannot restore {}: parent {} is removed".format(existing, phandler))
            existing.removed = False
            for cname in cls.CHILDREN_ATTRS:
                chandler = getattr(existing, cname, None)
                if chandler:
                    for c in chandler:
                        c.removed = False
                        session.add(c)

        cls._post_payload(existing, payload, s, client, storage)

        existing.payload = payload
        s.add(existing)
        s.flush()
        return existing
    
    CHILDREN_ATTRS = ('records', 'fields_list', 'values_list', 'media_list',)
    PARENT_ATTRS = ('form', 'record',)
    def remove(self, session):
        self.removed = True
        for cname in self.CHILDREN_ATTRS:
            chandler = getattr(self, cname, None)
            if chandler is not None:
               for c in chandler:
                    c.remove(session)
        session.add(self)
        session.flush()
        return self


class Project(BaseResource):
    """
    Fulcrum API Project
    see: https://developer.fulcrumapp.com/endpoints/projects/
    """
    __tablename__ = 'fulcrum_project'
    name = Column(String, index=True)
    description = Column(String(1024))
    MAPPED_COLUMNS = BaseResource.MAPPED_COLUMNS + ('name', 'description',)


class Form(BaseResource):
    """
    Fulcrum API Form
    see: https://developer.fulcrumapp.com/endpoints/forms/
    """
    __tablename__ = 'fulcrum_form'
    name = Column(String, index=True)
    description = Column(String(1024))
    fields = Column(JSON, nullable=False)
    MAPPED_COLUMNS = (BaseResource.MAPPED_COLUMNS +
                      ('name', 'description', ('elements', 'fields',),)
                      )

    @property
    def records_count(self):
        """
        Returns number of records for this form.
        """
        if self.removed:
            return len([r for r in self.records])
        return len([r for r in self.records if not r.removed])

    @classmethod
    def _post_payload(cls, instance, payload, session, client, storage):
        """
        Create field definitions from form's data.
        """
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
        out = []
        if url_params.get('form_id'):
            out.append(cls.id == url_params['form_id'])
        return out


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
        return 'Field({}, label={}, type={}, description={})'.format(self.id,
                                                                     self.label,
                                                                     self.type,
                                                                     self.description)
    
    @classmethod
    def _pre_payload(cls, payload, session, client, storage):
        # created_at is not populated anywhere, we'll use current timestamp.
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
        """
        Returns name of field in structure in record or None, if field is not media-type.

        Media field values contain id of media with media-type
        specific field, like in
        [{"photo_id":"a8d1df96-44e5-75e9-7312-7e2c5e902496,"caption": ""}]

        """
        if self.is_media:
            return '{}_id'.format(self.type.lower()[:-len('field')])
    
    @property
    def media_type(self):
        """
        media type name (photos, videos..)
        """
        mk = self.media_key
        if mk is None:
            return
        if mk == 'audio_id':
            return 'audio'
        return '{}s'.format(mk[:-3])

    @property
    def is_media(self):
        """
        Returns True if field contains media reference
        """
        return self.type in ('SignatureField', 'AudioField', 'PhotoField', 'VideoField',)

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
        """
        Return dictionary of label -> field value.
        Each field value is a dictionary from Value.get_value()
        """
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
        out = []
        if url_params.get('form_id'):
            out.append(cls.form_id == url_params['form_id'])
        if url_params.get('record_id'):
            out.append(cls.id == url_params['record_id'])

        if url_params.get('created_before'):
            out.append(cls.created_at < url_params['created_before'])
        if url_params.get('created_since'):
            out.append(cls.created_at > url_params['created_since'])

        if url_params.get('updated_before'):
            out.append(cls.updated_at < url_params['updated_before'])
        if url_params.get('updated_since'):
            out.append(cls.updated_at > url_params['updated_since'])

        if out:
            return [and_(*out)]
        return out

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

        # fetch media automatically
        fdef = Field.get(instance.field_id, session=session)
        mk = fdef.media_key
        if mk and instance.value:
            values = instance.value
            if isinstance(values, dict):
                values = [values]
            media_type = fdef.media_type
            mclient = getattr(client, media_type, None)
            for media in values:
                media_id = media[mk]
                if mclient:
                    data = mclient.find(media_id)
                    pdata = data[media_type.rstrip('s')].copy()
                    pdata['media_type'] = media_type.rstrip('s')
                    media = Media.from_payload(pdata, session, client, storage)



    def get_value(self, storage):
        """
        Returns dictionary with field value information:

        @param storage Storage instance to calculate paths and urls for media files

        * field key (short alphanumeric code)
        * description of field
        * label of field
        * type of field
        * value
        * list of media elements related

        Each media data contains:
        * id of media resource
        * caption from record
        * type of media (photo, audio, video, signature)
        * paths - per-size path/url values
        """
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
                m = media.get(mkey)
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

    @property
    def sizes(self):
        return self.SIZES[self.media_type]

    def get_path(self, storage, size):
        """
        Returns size-specific path to media file
        """
        return storage.get_path(self.form_id,
                                self.record_id,
                                self.media_type,
                                size,
                                self.content_type)

    def get_common_path(self, storage, size):
        """
        Returns common path in storage
        """
        return storage.get_common_path(self.form_id,
                                       self.record_id,
                                       self.media_type,
                                       size,
                                       self.content_type)

    def get_url(self, storage, size):
        """
        Returns size-specific url to media file
        """
        return storage.get_url(self.form_id,
                               self.record_id,
                               self.media_type,
                               size,
                               self.content_type)

    def get_paths(self, storage):
        """
        Return mapping of size->{path, url} for this media.
        """
        out = {}
        for s in self.sizes:
            out[s] = {'path': self.get_path(storage, s),
                      'url': self.get_url(storage, s)}
        return out

    def save_to_storage(self, storage, fhandle, size):
        """
        Shorthand to store file in storage
        @param storage Storage instance
        @param fhandle file-like object
        @param size name of size to save to
        """
        return storage.save(fhandle, self.form_id, self.record_id, self.media_type, size, self.content_type)

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

    @classmethod
    def get_q_params(cls, url_params, *args, **kwargs):
        out = []
        if url_params.get('form_id'):
            out.append(cls.form_id == url_params['form_id'])
        if url_params.get('record_id'):
            out.append(cls.record_id == url_params['record_id'])

        if url_params.get('photo_id'):
            out.append(and_(cls.id==url_params['photo_id'], cls.media_type == 'photo'))
        if url_params.get('video_id'):
            out.append(and_(cls.id==url_params['video_id'], cls.media_type == 'video'))
        if url_params.get('audio_id'):
            out.append(and_(cls.id==url_params['audio_id'], cls.media_type == 'audio'))
        if url_params.get('signature_id'):
            out.append(and_(cls.id==url_params['signature_id'], cls.media_type == 'signature'))
        return out


__all__ = ['Media', 'Value', 'Record', 'Field',
           'Project', 'Form', 'Base', 'Session']
