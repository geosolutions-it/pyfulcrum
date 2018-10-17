#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .models import Session, Base, Project
from sqlalchemy.engine import Engine, create_engine


class ApiManager(object):
    def __init__(self, db):
        if isinstance(db, Engine):
            self.db = db
        else:
            self.db = create_engine(db)
        Session.configure(bind=db)
        self.session = Session()
        Base.metadata.bind = db

    def create_project(self, name, description):
        p = Project(name=name, description=description)
        self.session.add(p)
        self.session.flush()
        return p

    def get_projects(self):
        return self.session.query(Project).all()
