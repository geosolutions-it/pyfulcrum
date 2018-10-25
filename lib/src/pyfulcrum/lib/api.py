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
    # default values for .from_payload used by subclasses
    default_item_args = {}
    # default values for client.seach()
    default_search_args = {}
    PER_PAGE = 50
    # identity key in item
    identity_key = 'id'

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
            # single objects are in envelope: singular path name
            # {'form': {..}}
            p = self.path
            if p.endswith('s'):
                p = p[:-1]
            if isinstance(data.get(p), dict):
                data = data[p]
            data.update(self.default_item_args)
            return self.model.from_payload(data, self.session, self.client, self.storage)
        return self.model.get(obj_id, session=self.session)
    
    def list(self, cached=True, generator=False, ignore_existing=False, *args, **kwargs):

        if self.path and not cached:
            def gen():
                # we're calling .search() which by default queries for all items
                # in collection, which may lead to timeouts for larger data sets.
                # to avoid that, we'll use paging with 50 items per page.
                # we have to inject paging params into url_params and loop until
                # we reach last page.
                url_params = kwargs.get('url_params') or {}
                url_params.update(self.default_search_args)
                url_params['per_page'] = self.PER_PAGE
                page = url_params.get('page') or 0
                url_params['page'] = page
                kwargs['url_params'] = url_params

                # initial value, which will be updated during fetch
                total_pages = page + 1

                while page < total_pages:
                    _items = self._handler.search(*args, **kwargs)
                    items = _items[self.path]
                    total_pages = _items['total_pages']
                    # sanity checks
                    if not items:
                        break
                    for i in items:
                        i = self._list_item(i)
                        # need to process full item payload from .find()
                        # because search() returns partial content
                        if ignore_existing:
                            v = self.get(i[self.identity_key])
                            if v is not None:
                                continue
                        v = self.get(i[self.identity_key], cached=False)
                        yield v
                    page +=1
                    url_params['page'] = page

            if generator:
                return gen()
            else:
                list(gen())
        return self.session.query(self.model).all()

    def _list_item(self, item):
        return item

class ProjectManager(BaseObjectManager):
    path = 'projects'
    model = Project


class FormManager(BaseObjectManager):
    path = 'forms'
    model = Form
    default_search_args = {'url_params': {'schema': 'false'}}


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
    model = Media
    default_item_args = {'media_type': 'video'}
    identity_key = 'access_key'


class PhotoManager(BaseObjectManager):
    path = 'photos'
    model = Media
    default_item_args = {'media_type': 'photo'}
    identity_key = 'access_key'


class AudioManager(BaseObjectManager):
    path = 'audio'
    model = Media
    default_item_args = {'media_type': 'audio'}
    identity_key = 'access_key'


class SignatureManager(BaseObjectManager):
    path = 'signatures'
    model = Media
    default_item_args = {'media_type': 'signature'}
    identity_key = 'access_key'


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
                PhotoManager,
                VideoManager,
                AudioManager,
                SignatureManager,
                )

    def __init__(self, db, client, storage_cfg):
        if isinstance(db, Engine):
            self.db = db
        else:
            self.db = create_engine(db)
        Session.configure(bind=self.db)
        self.session = Session()
        Base.metadata.bind = db
        self.client = client
        self.initialize_storage(storage_cfg)
        self.initialize_managers()

    def close(self):
        self.session.commit()

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

    @property
    def manager_names(self):
        out = []
        for el_cls in self.MANAGERS:
            out.append(el_cls.get_name())
        return out

    def get_manager(self, mgr_name):
        return getattr(self, mgr_name)

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
        return self.storage
