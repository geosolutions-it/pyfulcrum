#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .models import *
from sqlalchemy import Engine, create_engine


class ApiManager(object):
    def __init__(self, db):
        if isinstance(db, Engine):
            self.db = db
        else:
            self.db = create_engine(db)
        self.session = Session
        self.session.configure(bind=self.db)



    
