#!/usr/bin/env python
# -*- coding: utf-8 -*-

from fulcrum import Fulcrum as FC
from .models import Session, Base, Project, Form, Record, Media, Field
from sqlalchemy.engine import Engine, create_engine
from .storage import Storage
from .formats import FORMATS


PER_PAGE = 50

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
    # identity key in item
    identity_key = 'id'

    @classmethod
    def get_name(cls):
        return cls.path or cls.__name__[:-len('manager')].lower()

    def __init__(self, session, client, storage):
        """
        @param session - DB session
        @param client - Fulcrum API client
        @param storage - Storage handler
        """
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

    def get(self, obj_id, cached=True, if_removed=False):
        """
        Retrieve 
        """
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
        return self.model.get(obj_id, session=self.session, if_removed=if_removed)

    def remove(self, obj_id, cached=True, *args, **kwargs):
        obj = self.get(obj_id, cached=True)
        if obj:
            return obj.remove(self.session)

    def list(self, cached=True, generator=False, ignore_existing=False, flush=False, is_spatial=False, *args, **kwargs):
        """
        Return list of resources.
        This will return list or generator of resources in local db.

        @param cached - boolean (default: True) if set to False, first Fulcrum API will be
                        called to fetch all data, then return all data from db.
                        If set to True, only local db query is executed.

        @param generator - booleand (default: False) if set to True, generator will be returned
                        instead of list. This will optimize cases when large data sets are going
                        to be returned.

        @param ignore_existing - boolean (default: False) or list to be used with cached=False. In case
                        both switches are in use, ignore_existing will cause that only items
                        present in Fulcrum API are going to be live-queried, so no existing data
                        update will be performed.
                        If ignore_existing is a list, existing items will be appended to the list.


        @param url_params - dict with query params for Fulcrum API client. By default, paging
                        of results is enabled and 50 items per page are expected.

        """
        if self.path and not cached:
            def gen():
                # we're calling .search() which by default queries for all items
                # in collection, which may lead to timeouts for larger data sets.
                # to avoid that, we'll use paging with 50 items per page.
                # we have to inject paging params into url_params and loop until
                # we reach last page.
                url_params = kwargs.get('url_params') or {}
                url_params.update(self.default_search_args)
                url_params['per_page'] = PER_PAGE
                _page = url_params.get('page')
                page = _page or 0
                url_params['page'] = page
                kwargs['url_params'] = url_params

                # initial value, which will be updated during fetch
                total_pages = page + 1

                while page < total_pages:
                    _items = self._handler.search(*args, **kwargs)
                    items = _items[self.path]
                    if not _page:
                        total_pages = _items['total_pages']
                    # sanity checks
                    if not items:
                        break
                    for i in items:
                        i = self._list_item(i)
                        # need to process full item payload from .find()
                        # because search() returns partial content
                        if ignore_existing in (True, []):
                            v = self.get(i[self.identity_key])
                            if v is not None:
                                if isinstance(ignore_existing, list):
                                    ignore_existing.append(i[self.identity_key])
                                continue
                        v = self.get(i[self.identity_key], cached=False)
                        if flush:
                            self.session.commit()
                        if is_spatial and hasattr(self.model, 'point') and not v.point:
                            continue
                        yield v
                    page +=1
                    url_params['page'] = page

            if generator:
                return gen()
            else:
                list(gen())
        if kwargs.get('url_params'):
            up = kwargs.get('url_params')
            params = self.model.get_q_params(up)
            return self.get_query(is_spatial=is_spatial).order_by('updated_at').filter(self.model.removed == False).filter(*params)
        return self.get_query(is_spatial=is_spatial).order_by('updated_at').filter(self.model.removed == False)

    def _list_item(self, item):
        return item

    def list_removed(self, *args, **kwargs):
        """
        Return removed items
        """
        
        if kwargs.get('url_params'):
            up = kwargs.get('url_params')
            params = self.model.get_q_params(up)

            return self.get_query().order_by('updated_at').filter(self.model.removed == True).filter(*params)
        return self.get_query().order_by('updated_at').filter(self.model.removed == True)


    def get_query(self, session=None, is_spatial=False):
        if session is None:
            session = self.session
        q = session.query(self.model)
        if is_spatial and getattr(self.model, 'point', None) is not None:
            q = q.filter(self.model.point != None)
        if self.default_item_args:
            return q.filter_by(**self.default_item_args)
        return q

    def sync(self):
        """
        Synchronize local db and remote
        """
        existing = []
        # this is very naive approach, because .list invocation will only add new
        # items if they're present in API. It won't mark any items removed. To 
        # do full synchronization, it should be two-way - first remove items
        # present locally but not in API, then add items not present locally.
        # That's why this method is not exposed anywhere.
        self.list(cached=False, ignore_existing=existing)
        

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

    def __init__(self, db, client, storage):
        if isinstance(db, Engine):
            self.db = db
        else:
            self.db = create_engine(db)
        Session.configure(bind=self.db)
        self.session = Session()
        Base.metadata.bind = db
        if isinstance(client, str):
            client = FC(client)
        self.client = client
        self.initialize_storage(storage)
        self.initialize_managers()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if args[0]:
            self.rollback()
        else:
            self.flush()

    def rollback(self):
        self.session.rollback()

    def flush(self):
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
    
    @classmethod
    def get_manager_names(cls):
        out = []
        for el_cls in cls.MANAGERS:
            out.append(el_cls.get_name())
        return out

    @property
    def manager_names(self):
        return ApiManager.get_manager_names()

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
        if isinstance(cfg, str):
            elements = cfg.split(';', 1)
            if not len(elements) in (1,2):
                raise ValueError('String configuration is invalid')
            cfg = {}  
            cfg['root_dir'] = elements.pop(0)
            if elements:
                cfg['url_base'] = elements.pop(0)

        if not isinstance(cfg, dict):
            raise TypeError("Storage configuration should be a dictionary")
        storage_cfg = {}
        storage_cfg['root_dir'] = str(cfg['root_dir'])
        storage_cfg['url_base'] = cfg.get('url_base')
        self.storage = Storage(**storage_cfg)
        return self.storage

    def as_format(self, format, item, multiple=False, *args, **kwargs):
        formatter = self.get_formatter(format)
        return formatter(item, self.storage, multiple, *args, **kwargs)

    def get_formatter(self, format_name):
        return FORMATS[format_name]
