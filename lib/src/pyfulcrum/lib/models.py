#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sqlalchemy import (Column, Integer, String,
                        DateTime, Numeric, ForeignKey,
                        JSON, Enum)
from sqlalchemy.orm import relationship
from sqlalchemy.schema import MetaData
from sqlalchemy.orm.session import sessionmaker

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from geoalchemy2 import Geometry

md = MetaData()
Session = sessionmaker()

Base = declarative_base(metadata=md)


class BaseResource(object):
    # name of identity column (which may be different from id
    MAPPED_COLUMNS = (('id', 'id',),
                      ('created_at', 'created_at',),
                      ('updated_at', 'updated_at',),
                      )

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
    payload = Column(JSON, nullable=True)

    def __str__(self):
        return u'{}({})'.format(self.__class__.__name__, self.id)

    __repr__ = __str__

    @classmethod
    def get(cls, id, session=None):
        s = session or Session()
        return s.query(cls).filter(cls.id==id).first()

    @classmethod
    def _post_payload(cls, instance, payload, session):
        pass


    @classmethod
    def _pre_payload(cls, payload, session):
        return payload

    @classmethod
    def from_payload(cls, payload, session=None):
        s = session or Session()

        # hook for preprocessing class-specific payload
        payload = cls._pre_payload(payload, s)
        
        id = payload['id']
        existing = cls.get(id, session=s)
        if not existing:
            existing = cls(id=id, payload=payload)
        for m in cls.MAPPED_COLUMNS:
            if isinstance(m, (list,tuple,)):
                mdest, msrc = m
            else:
                mdest = msrc = m
            setattr(existing, mdest, payload[msrc])
        
        # hook for subclasses
        cls._post_payload(existing, payload, s)
        
        s.add(existing)
        s.flush()
        return existing


class Project(BaseResource, Base):
    __tablename__ = 'fulcrum_project'
    name = Column(String)
    description = Column(String(1024))
    MAPPED_COLUMNS = BaseResource.MAPPED_COLUMNS + ('name','description',)

    @classmethod
    def _pre_payload(cls, payload, session):
        return payload['project']

class Form(BaseResource, Base):
    __tablename__ = 'fulcrum_form'
    name = Column(String)
    description = Column(String(1024))
    fields = Column(JSON, nullable=False)
    MAPPED_COLUMNS = BaseResource.MAPPED_COLUMNS +\
                      ('name', 'description', 'fields')

    @classmethod
    def _pre_payload(cls, payload, session):
        form_f = payload['form']
        return form_f


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


class Field(BaseResource, Base):
    __tablename__ = 'fulcrum_field'
    form_id = Column(String, ForeignKey('fulcrum_form.id'), nullable=False)
    name = Column(String, nullable=False)
    type = Column(FieldTypeEnum, nullable=False)
    form = relationship(Form, backref="fields_list")


class Record(BaseResource, Base):
    __tablename__ = 'fulcrum_record'
    form_id = Column(String, ForeignKey('fulcrum_form.id'), nullable=False)
    project_id = Column(String,
                        ForeignKey('fulcrum_project.id'),
                        nullable=True)
    point = Column(Geometry('POINT'), nullable=True)
    altitude = Column(Integer, nullable=True)
    speed = Column(Numeric, nullable=True)
    course = Column(Numeric, nullable=True)
    values = Column(JSON, nullable=True)
    status = Column(String, nullable=True)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=True)
    assigned_by = Column(String, nullable=True)
    form = relationship(Form, backref="records")
    project = relationship(Project, backref="records")


class Value(BaseResource, Base):
    __tablename__ = 'fulcrum_value'
    field_id = Column(String,
                      ForeignKey('fulcrum_field.id'),
                      nullable=False)
    record_id = Column(String,
                       ForeignKey('fulcrum_record.id'),
                       nullable=False)
    value = Column(String, nullable=False, default='')
    type = Column(FieldTypeEnum, nullable=False)
    meta = Column(JSON, nullable=False)
    field = relationship(Field, backref='values_list')
    record = relationship(Record, backref='values_list')


class Media(BaseResource, Base):
    MEDIA_PHOTO = 'photo'
    MEDIA_AUDIO = 'audio'
    MEDIA_VIDEO = 'video'
    MEDIA_TYPES = (MEDIA_PHOTO, MEDIA_AUDIO, MEDIA_VIDEO,)
    KEY_COLUMN = 'access_key'

    __tablename__ = 'fulcrum_media'
    # access_key = Column(String, nullable=False, unique=True)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=True)
    bbox = Column(Geometry('POLYGON'), nullable=True)
    field_id = Column(String, ForeignKey('fulcrum_field.id'), nullable=False)
    record_id = Column(String,
                       ForeignKey('fulcrum_record.id'),
                       nullable=False)
    form_id = Column(String, ForeignKey('fulcrum_form.id'), nullable=False)
    file_size = Column(Integer, nullable=False)
    url = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    track = Column(Geometry('LINESTRING'), nullable=True)
    media_type = Column(Enum(*MEDIA_TYPES, name='media_types'), nullable=False)
    storage = Column(String, nullable=False)


__all__ = ['Media', 'Value', 'Record', 'Field',
           'Project', 'Form', 'Base', 'Session']
