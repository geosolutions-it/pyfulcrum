
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from geoalchemy2 import Geometry

Session = sessionmaker()

Base = declarative_base()


class BaseResource(object):
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), null=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), null=False, server_default=func.now(), onupdate=func.now())
    fetched_at = Column(DateTime(timezone=True), null=True, server_default=func.now(), onupdate=func.now())
    payload = Column(JSON, null=True)


class Project(BaseResource, Base):
    __tablename__ = 'fulcrum_project'
    name = Column(String)
    description = Column(String, max_length=1024)


class Form(BaseResource, Base):
    __tablename__ = 'fulcrum_form'
    name = Column(String)
    description = Column(String, max_length=1024)
    fields = Column(JSON, null=False)
    

class Field(BaseResource, Base):
    __tablename__ = 'fulcrum_field'
    FIELD_TYPES = ("TextField", "YesNoField", "Label",
                   "Section", "ChoiceField", "ClassificationField",
                   "PhotoField", "VideoField", "AudioField",
                   "BarcodeField", "DateTimeField", "TimeField",
                   "Section", "Repeatable", "AddressField",
                   "SignatureField", "HyperlinkField",
                   "CalculatedField", "RecordLinkField",)
    form_id = Column(Integer, ForeignKey('fulcrum_form.id'), null=False)
    name = Column(String, null=False)
    type = Column(Enum(FIELD_TYPES), null=False)
    form = relationship(Form, back_populates="fields_list")
   

class Record(BaseResource, Base):
    __tablename__ = 'fulcrum_record'
    form_id = Column(Integer, ForeignKey('fulcrum_form.id'), null=False)
    project_id = Column(Integer, ForeignKey('fulcrum_project.id'), null=True)
    point = Column(Geometry('POINT'), null=True)
    altitude = Column(Integer, null=True)
    speed = Column(Numeric, null=True)
    course = Column(Numeric, null=True)
    values = Column(JSON, null=True)
    status = Column(String, null=True)
    created_by = Column(String, null=False)
    updated_by = Column(String, null=True)
    assigned_by = Column(String, null=True)
    form = relationship(Form, back_populates="records")
    project = relationship(Project, back_populates="records")


class Value(BaseResource):
    __tablename__ = 'fulcrum_value'
    field_id = Column(Integer, ForeignKey('fulcrum_field.id'), null=False)
    record_id = Column(Integer, ForeignKey('fulcrum_record.id'), null=False)
    value = Column(String, null=False, default='')
    type = Column(Enum(Field.FIELD_TYPES), null=False)
    metadata = Column(JSON, null=False)
    field = relationship(Field, back_populates='values_list')
    record = relationship(Record, back_populates='values_list')


class Media(BaseResource, Base):
    MEDIA_PHOTO = 'photo'
    MEDIA_AUDIO = 'audio'
    MEDIA_VIDEO = 'video'
    MEDIA_TYPES = (MEDIA_PHOTO, MEDIA_AUDIO, MEDIA_VIDEO,)

    __tablename__ = 'fulcrum_media'
    access_key = Column(String, null=False, unique=True)
    created_by = Column(String, null=False)
    updated_by = Column(String, null=True)
    bbox = Column(Geometry('POLYGON'), null=True)
    field_id = Column(Integer, ForeignKey('fulcrum_field.id'), null=False)
    record_id = Column(Integer, ForeignKey('fulcrum_record.id'), null=False)
    form_id = Column(Integer, ForeignKey('fulcrum_form.id'), null=False)
    file_size = Column(Integer, null=False)
    url = Column(String, null=False)
    content_type = Column(String, null=False)
    track = Column(Geometry('LINESTRING'), null=True)
    media_type = Column(Enum(*MEDIA_TYPES), null=False)
    storage = Column(String, null=False)

__all__ = ['Media', 'Value', 'Record', 'Field', 'Project', 'Form', 'Base', 'Session']
