#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .models import Session, Base, Project, Form, Record, Media, Field
from sqlalchemy.engine import Engine, create_engine
from .storage import Storage


class BaseObjectManager(object):
    """
    Base class for API object managers. Base class
    connects fulcrum api objects and db models. Subclass
    will handle object-specific variations of handler.
    """
    path = None
    model = None

    @classmethod
    def get_name(cls):
        return cls.path or cls.__name__[:-len('manager')].lower()

    def __init__(self, session, client, storage):
        self.session = session
        self.client = client
        self.storage = storage
        self._handler = self._get_handler()

    def _get_handler(self):
        if self.path is None:
            return
        h = getattr(self.client, self.path, None)
        if h is None:
            raise ValueError("invalid object path: {}".format(self.path))
        return h

    def get(self, obj_id, cached=True):
        if self.path and not cached:
            data = self._handler.find(obj_id)
            return self.model.from_payload(data, self.session, self.client, self.storage)
        return self.model.get(obj_id, session=self.session)

    def list(self, cached=True, *args, **kwargs):
        if self.path and not cached:
            items = self._handler.search(*args, **kwargs)
            for i in items:
                self.get(i['id'], cached=False)
        return self.session.query(self.model).all()


class ProjectManager(BaseObjectManager):
    path = 'projects'
    model = Project


class FormManager(BaseObjectManager):
    path = 'forms'
    model = Form


class FieldsManager(BaseObjectManager):
    """
    This is special case of Resource Manager.
    Field is not reachable in Fulcrum API, but
    we'll have manager for convenience.
    """
    path = None
    model = Field


class RecordManager(BaseObjectManager):
    path = 'records'
    model = Record


class VideoManager(BaseObjectManager):
    path = 'videos'
    models = Media


class PictureManager(BaseObjectManager):
    path = 'pictures'
    models = Media


class AudioManager(BaseObjectManager):
    path = 'audio'
    model = Media


class ApiManager(object):
    """
    This is entry point class for accessing PyFulcrum data.
    It handles db connection and Fulcrum API credentials
    (to be implemented), which should be provided by caller code.
    """

    MANAGERS = (ProjectManager,
                FormManager,
                FieldsManager,
                RecordManager,
                PictureManager,
                VideoManager,
                AudioManager,
                )

    def __init__(self, db, client, storage_cfg):
        if isinstance(db, Engine):
            self.db = db
        else:
            self.db = create_engine(db)
        Session.configure(bind=db)
        self.session = Session()
        Base.metadata.bind = db
        self.client = client
        self.initialize_storage(storage_cfg)
        self.initialize_managers()

    def create_project(self, id, name, description):
        p = Project(id=id, name=name, description=description)
        self.session.add(p)
        self.session.flush()
        return p

    def get_projects(self, cached=True):
        if cached:
            return self.get_projects_cached()
        return self.get_projects_live()

    def get_projects_live(self):
        return self.get_projects_cached()

    def get_projects_cached(self):
        return self.session.query(Project).all()

    def initialize_managers(self):
        for el_cls in self.MANAGERS:
            el_name = el_cls.get_name()
            el_inst = el_cls(self.session, self.client, self.storage)
            setattr(self, el_name, el_inst)

    def initialize_storage(self, cfg):
        if isinstance(cfg, Storage):
            self.storage = cfg
            return
        if not isinstance(cfg, dict):
            raise TypeError("Storage configuration should be a dictionary")
        storage_cfg = {}
        storage_cfg['root_dir'] = str(cfg['root_dir'])
        storage_cfg['url_base'] = cfg.get('url_base')
        self.storage = Storage(**storage_cfg)
