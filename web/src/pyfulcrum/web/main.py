#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from flask import abort, current_app, Response, request, Flask
from .webhooks import webhooks


CONFIG_ENV_VAR = 'PYFULCRUM_WEB_CONFIG'


def make_app():
    app = Flask(__name__)
    app.config.from_envvar(CONFIG_ENV_VAR, silent=False)
    app.register_blueprint(webhooks)

    return app


def main():
    try:
        port = sys.argv[1]
    except IndexError:
        port = None
    app = make_app()
    app.run(port=port, debug=True)


if __name__ == '__main__':
    main()
