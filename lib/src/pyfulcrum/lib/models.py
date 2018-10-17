
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, JSON, Enum
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
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    fetched_at = Column(DateTime(timezone=True), nullable=True, server_default=func.now(), onupdate=func.now())
    payload = Column(JSON, nullable=True)


class Project(BaseResource, Base):
    __tablename__ = 'fulcrum_project'
    name = Column(String)
    description = Column(String(1024))


class Form(BaseResource, Base):
    __tablename__ = 'fulcrum_form'
    name = Column(String)
    description = Column(String(1024))
    fields = Column(JSON, nullable=False)
    
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
    form_id = Column(Integer, ForeignKey('fulcrum_form.id'), nullable=False)
    name = Column(String, nullable=False)
    type = Column(FieldTypeEnum, nullable=False)
    form = relationship(Form, backref="fields_list")
   

class Record(BaseResource, Base):
    __tablename__ = 'fulcrum_record'
    form_id = Column(Integer, ForeignKey('fulcrum_form.id'), nullable=False)
    project_id = Column(Integer, ForeignKey('fulcrum_project.id'), nullable=True)
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


class Value(BaseResource):
    __tablename__ = 'fulcrum_value'
    field_id = Column(Integer, ForeignKey('fulcrum_field.id'), nullable=False)
    record_id = Column(Integer, ForeignKey('fulcrum_record.id'), nullable=False)
    value = Column(String, nullable=False, default='')
    type = Column(FieldTypeEnum, nullable=False)
    metadata = Column(JSON, nullable=False)
    field = relationship(Field, backref='values_list')
    record = relationship(Record, backref='values_list')


class Media(BaseResource, Base):
    MEDIA_PHOTO = 'photo'
    MEDIA_AUDIO = 'audio'
    MEDIA_VIDEO = 'video'
    MEDIA_TYPES = (MEDIA_PHOTO, MEDIA_AUDIO, MEDIA_VIDEO,)

    __tablename__ = 'fulcrum_media'
    access_key = Column(String, nullable=False, unique=True)
    created_by = Column(String, nullable=False)
    updated_by = Column(String, nullable=True)
    bbox = Column(Geometry('POLYGON'), nullable=True)
    field_id = Column(Integer, ForeignKey('fulcrum_field.id'), nullable=False)
    record_id = Column(Integer, ForeignKey('fulcrum_record.id'), nullable=False)
    form_id = Column(Integer, ForeignKey('fulcrum_form.id'), nullable=False)
    file_size = Column(Integer, nullable=False)
    url = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    track = Column(Geometry('LINESTRING'), nullable=True)
    media_type = Column(Enum(*MEDIA_TYPES, name='media_types'), nullable=False)
    storage = Column(String, nullable=False)

__all__ = ['Media', 'Value', 'Record', 'Field', 'Project', 'Form', 'Base', 'Session']
