# PyFulcrum Web Application

## Introduction

PyFulcrum Web application is a two-component application. One component is webhook receiver that can be configured in Fulcrum to receive updates on specific resources, second is API endpoints from PyFulcrum library exposed through HTTP (only fragment of the whole API), also with media files available. Both parts are available as [Flask Blueprints](http://flask.pocoo.org/docs/1.0/blueprints/#blueprints) objects, so they can be incorporated into bigger application if needed.

### Requirements

* PyFulcrum lib and it's requirements
* Flask
* web server to serve statics and web application (nginx + uwsgi are preferred)


### Installation

PyFulcrum web application requires working installation of PyFulcrum lib. Following steps assume deployment will be using nginx and uwsgi packages.

1. Pefrorm steps from [PyFulcrum lib installation](https://github.com/geosolutions-it/pyfulcrum/tree/master/lib#installation), using `/usr/local/pyfulcrum` directory as a work directory and `/usr/local/pyfulcrum/htdocs/storage` as storage directory. We will reuse database and virtualenv from that installation.

1. Install PyFulcrum web application requirements and application itself

    ```
    venv/bin/pip install -r repo/pyfulcrum/web/requirements.txt
    venv/bin/pip install -e repo/pyfulcrum/web/
    ```

1. Install uwsgi and nginx packages:

    Debian-derived:

    ```
    apt-get install uwsgi-plugin-python3 nginx
    ```

    Or RedHat/CentOS:
    ```
    yum install nginx uwsgi-plugin-python3
    ```

1. Configure web application. Web application requires configuration file to be present and to contain location of storage, Fulcrum API key and database url. See [Web application configuration](#configuration) for details.
    
1. Configure uwsgi. UWSGI requires app configuration file. Sample file is in `repo/pyfulcrum/web/files/pyfulcrum-web.ini`. You need to adjust paths, socket location and plugin name if needed.
    Target location depends on your operating system, but usually Debian-derived systems use `/etc/uwsgi/apps-enabled/` directory to store application configuration, while RH-based use `/etc/uwsgi.d/` for the same purpose. Note that Debian-derived systems usually enforce socket path for uwsgi applications.

1. Configure nginx. Nginx requires vhost configuration file. Sample file is in `repo/pyfulcrum/nginx.site.conf`. You need to adjust `server_name`, `root` and upstream sockets locations to match your deployment. Note that API application doesn't require any authentication, so you may want to enforce user authentication in web server for this purpose. 

    Target location depends on your operating system, but usually Debian-derived systems use `/etc/nginx/sites-enabled/` directory to store vhost configuration, while RH-based use `/etc/nginx/conf.d` for the same purpose.

1. Restart uwsgi and nginx services:

    ```
    service uwsgi restart
    service nginx restart
    ```

Application deployed in this way can be updated in following way:

1. Go to repository directory and update code base:

    ```
    cd repo/pyfulcrum
    git pull
    ```

1. Run migrations if needed:

    ```
    cd repo/pyfulcrum/lib
    ../../venv/bin/alembic -c local-db.ini upgrade head
    ```

1. Update web application `main.py` file to enforce reload of uwsgi, so it will use new code:

    ```
    touch repo/pyfulcrum/web/src/pyfulcrum/web/main.py 
    ```


### Configuration

PyFulcrum webapp blueprints require configuration data, which provides database url, path to storage/storage base url and Fulcrum API key. Due to a fact that components are implemented as blueprints, they expect configuration will be provided by application that incorporates them as blueprints. In any case, each blueprint requires specific keys to be present in `current_app.config` mapping.

By default (using `pyfulcrum.web.main` module) Flask application expects configuration to be provided as a file with key=value format, which will be parsed on application load. Each blueprint is indenpendent, so configuration may seem to be repeated. This is however to provide more flexibility in deployment and application composition.

Sample configuration is available in `web/files/config.sample.cfg`.

#### Webhooks configuration

Webhook blueprint allows to handle multiple webhooks. Each webhook has a distinct name, and can point to different location. Name can be any set of chars, and for security reasons (Fulcrum application doesn't provide any means to authenticate webhook call from their side, other than using unique token in webhook URL), it's recommended to use random string. Configuration expects name to be present in webhook config key, so keys are constructed using following template (we'll use `$NAME` as a placeholder for actual name):

```
WEBHOOK_$NAME_DB="postgresql://pyfulcrum:pyfulcrum@localhost/pyfulcrum"
WEBHOOK_$NAME_CLIENT="XXXxxxXXXxxx"
WEBHOOK_$NAME_STORAGE="/path/to/storage;http://server/storage/"
```

* `WEBHOOK_$NAME_DB` is database url, similar to one provided in PyFulcrum lib.
* `WEBHOOK_$NAME_CLIENT` is Fulcrum API key
* `WEBHOOK_$NAME_STORAGE` is a string containing path to storage and optional base url which is used to serve storage files via HTTP server. Both values are separated with `;` sign. 

Internally, webhook receives `$NAME` as call parameter, then it retrives per-webhook configuration using [pseudo-namespace](http://flask.pocoo.org/docs/1.0/api/#flask.Config.get_namespace) constructed with `WEBHOOK_$NAME_` string. If there's no configuration for given namespace, webhook call will be considered invalid. If configuration exists, it will be processed.
##### Including/excluding objects handled by webhook

Webhook configuration allows to provide list of objects (for example, forms) that should be only/should not be processed by webhook. This is configurable with two config variables, `WEBHOOK_$NAME_INCLUDE_OBJECTS` and `WEBHOOK_$NAME_EXCLUDE_OBJECTS`. Each value in variable should have a a form `resource_type:id1,id2,..;resource_type:id1,id2`. For example, to handle updates on two specific forms only, you should set variable to

```
WEBHOOK_$NAME_INCLUDE_OBJECTS="form:$form1_id,$form2_id"
```

where `$form1_id` and `$form2_id` are identifiers of those forms. This will also work for related resources, like record or media files. They will be processed, only if form they're referencing is one of those forms.

To ignore specific forms, you should add similar configuration to `WEBHOOK_$NAME_EXCLUDE_OBJECTS`.

If both variables are provided in configuration, resource will be checked for include list first (so whitelist check will be performed first). If whitelist is empty, blacklist mode is performed.

#### API configuration

API blueprint requires similar configuration paris as webhook, although only one API instance is created, so only one configuration key-value set is needed.

```
API_DB="postgresql://pyfulcrum:pyfulcrum@localhost/pyfulcrum"
API_CLIENT="XXXxxxXXXxxx"
API_STORAGE="/path/to/storage;http://server/storage/"
```

## Notes

### PyFulcrum webhook application

Webhook receiver allows to synchronize data in your Fulcrum account with local copy. Mind that your Fulcrum plan must enable webhooks (see [developer documentation for details](https://developer.fulcrumapp.com/general/webhooks/).). Follow instructions from Fulcrum to set up webhook there. 

As stated above, there can be several webhook receivers with different configuration. Base webhook url is `/webhook/$name/`, where `$name` is a varying part, and corresponds to `$NAME` part in webhook configuration. So, for example, if you have following configuration:

```
WEBHOOK_MYWEBHOOK1_DB="postgresql://pyfulcrum:pyfulcrum@localhost/pyfulcrum"
WEBHOOK_MYWEBHOOK1_CLIENT="XXXxxxXXXxxx"
WEBHOOK_MYWEBHOOK1_STORAGE="/path/to/storage;http://my.web.server/storage/"
```

and web application is deployed under `http://my.web.server`, then your webhook url will be `http://my.web.server/webhook/mywebhook/`.

When webhook is received (see [webhooks documentation](https://developer.fulcrumapp.com/general/webhooks/#events) for details on event types and sample payloads), it's payload is parsed, and two values are extracted: event type (from `type` path) and item id (from `data.id` path). Internally, webhook receiver will call PyFulcrum API client to fetch fresh payload for given item id. Due to limited security around webhook dispatching, payload from webhook is not considered as secure, and so the only reasonable way to validate payload is to fetch object pointed in payload directly from Fulcrum API.

### API

API web application is fairly simple, it's exposes PyFulcrum's library resources list method (`pyfulcrum.lib.api.BaseResource.list`). API will return ONLY CACHED values, no live requests are made to Fulcrum API. If configured properly, media files links should be served by web server as well. 
Following endpoints are available:

* `/api/forms/` - list of forms
* `/api/records/` - list of records
* `/api/projects/` - list of projects
* `/api/photos/` - list of photos
* `/api/videos/` - list of videos
* `/api/audio/` - list of audio
* `/api/signatures/` - list of signatures


Each endpoint can be served in varions formats. Format can be controlled by setting `format` query param. By default, `json` format is used. Data can be retrived in several formats:


 Format | Description | Returns only spatial-enabled items 
 ------ | ----------- | --- 
 `raw` | Raw Fulcrum API payload for objects stored | No 
 `json` | PyFulcrum-flavor of JSON for objects stored. This will contain processed media links. | No 
 `csv` | Returns CSV with all objects for resource, and it doesn't support paging. | No 
 `geojson` | This will return `GeoJSON` `FeatureCollection` with records that have proper spatial location set. Note, this will work only for Records. | Yes 
 `kml` | This will return `KML` format with records that have proper spatial location set. Note, this will work only for Records, and it doesn't support paging. | Yes 
 `shp` | this will return `ESRI Shapefile` format with records that have proper spatial location set. Note, this will work only for Records, and it doesn't support paging. | Yes


Summary of supported formats per resource type


 Resource type | URL | formats | Spatial-aware | allowed filtering args 
 ------------- | --- | ------- | ------------  | ---
 Forms | `/api/forms/` | `raw`, `json`, `csv` | No | `form_id` 
 Records | `/api/records/` | `raw`, `json`, `geojson`, `kml`, `shp` | Yes | `form_id`, `record_id`, `created_since`, `created_before`, `updated_since`, `updated_before` 
 Projects | `/api/projects/` | `raw`, `json`, `csv` | No | - 
 Photos | `/api/photos/` | `raw`, `json`, `csv` | No | `record_id`, `form_id` 
 Audio | `/api/audio/` | `raw`, `json`, `csv` | No | `record_id`, `form_id` 
 Videos | `/api/videos/` | `raw`, `json`, `csv` | No | `record_id`, `form_id` 
 Signatures | `/api/signatures/` | `raw`, `json`, `csv` | No | `record_id`, `form_id`


Additionally, each endpoint supports (excluding various exceptions) paging with following query params:

* `page` - 0-based page number index (default: `0`)
* `per_page` - number of items per page. Default is `50`.

Response, if any json is used, usually comes within following envelope:

```
{"page": 0,
 "per_page": 50,
 "total_pages": 123,
 "total": 6150,
 "items": []}
```

With exception for `GeoJSON`, which will return items as `features` key.


##### Examples:

* retrive list of forms as Fulcrum API payload:

```
GET http://your.server/api/forms?format=raw
```

* retrive list of records as Fulcrum API payload for given form:

```
GET http://your.server/api/records?format=raw&form_id=xxxxXXXxxxx
```

* retrive list of records as Fulcrum API payload for given form, 10th page (indexed from 0):

```
GET http://your.server/api/records?format=raw&form_id=xxxxXXXxxxx&page=9
```

* retrive list of records as shapefile for given form. Because this list response is paged, this will produce shapefile with 50 features on it.:

```
GET http://your.server/api/records?format=shp&form_id=xxxxXXXxxxx
```

* retrive list of at most 500 records as shapefile for given form. You can generate another 500 records by modifying `page` parameter:

```
GET http://your.server/api/records?format=shp&form_id=xxxxXXXxxxx&per_page=500&page=0
```

Note that spatial formats, especially shapefile and kml, take significant time to create. If number of records is too big, server may return timeout (http 502 error) instead.

* Retrive specific record from records list:

```
GET http://your.server/api/records/?format=json&form_id=xxxxXXXxxxxx&record_id=yyyyYYYyyyyy
```

## Notes

### Offloading data synchronization to task queue

Webhook implementation is synchronous. At the moment, it’s fast enough to work in that mode. However, if in the future this solution would turn out to be underperformant, part of webhook handling logic can be moved to task queue. Flask has quite good [integration with Celery](http://flask.pocoo.org/docs/1.0/patterns/celery/) and [RQ](https://flask-rq2.readthedocs.io/en/latest/). In order to integrate existing code, `pyfulcrum.web.webhooks._handle_webhook()` should be decorated with proper task decorator, and called from `pyfulcrum.web.webhooks.fulcrum_call` as asynchronous task. This requires handling task queue configuration in web application that is calling webhook blueprint, and webhook code should be updated as well. Also, Redis would be needed as additional deployment component.
