# PyFulcrum

## Introduction

PyFulcrum is a python library that fetches contents from Fulcrum API (https://www.fulcrumapp.com/) and saves it to local database/storage. It also exposes own API to update and retrive saved content. 


## Requirements

PyFulcrum requires:
 * python newest 3.x interpreter (written with python 3.6)
 * GDAL 2.x with development package (python bindings will be provided by pygdal)
 * Fulcrum API key (see https://developer.fulcrumapp.com/api/intro/#authentication)
 * Local storage with considerable amount of free space (depending on amount of media files stored in Fulcrum).
 * PostgreSQL 9.6 + PostGIS database cluster

## Installation

 Installation is simple:

 1. Obtain Fulcrum API key
 1. Create directory for storage

    ```
    mkdir -p /path/to/storage/dir
    ```

 1. Clone PyFulcrum repo

    ```
    git clone https://github.com/geosolutions-it/pyfulcrum.git
    ```

 1. Enter `lib` direcotry and create venv

    ```
    cd lib
    python3 -m venv venv
    ```

 1. Obtain gdal version and install according version of pygdal (see https://github.com/nextgis/pygdal):

    ```
    gdal-config --version
    venv/bin/pip install pygdal==$(gdal-config --version)
    ```

 1. Install dependencies and pyfulcrum library:

    ```
    venv/bin/pip install -r requirements.txt
    venv/bin/pip install -e .
    ```

 1. Copy `alembic.ini` to `local-db.ini` and replace `sqlalchemy.url` value to value adjusted to your database.

    ```
    cp alembic.ini local-db.ini
    $ cat local-db.ini | grep sqlalchemy
    sqlalchemy.url = postgresql://pyfulcrum:pyfulcrum@localhost/pyfulcrum
    ```

 1. Create `pyfulcrum` database (with `pyfulcrum` user) and apply database model migrations (this will create required tables in database):

    ```
    psql -U postgres -c "create user pyfulcrum superuser login password 'pyfulcrum'; create database pyfulcrum owner pyfulcrum;"
    psql -U pyfulcrum -c "create extension postgis;"
    venv/bin/alembic -c local-db.ini upgrade head
    ```

## PyFulcrum API

PyFulcrum is a library containing several components: database models which store objects from Fulcrum API with basic metadata, API Manager layer, which acts as a gateway API and transparent cache for Fulcrum API objects, CLI application and formatters which allow to export data in different formats.

In day-to-day usage, you should use PyFulcrum API through `pyfulcrum.lib.api.APIManager` class:

### ApiManager creation

```
from fulcrum import Fulcrum
from pyfulcrum.lib.api import ApiManager

client = Fulcrum(FULCRUM_API_KEY)
api = ApiManager(DB_URL, client, {'root_dir': STORAGE_ROOT_DIR, 'url_base': STORAGE_URL_LOCATION})
```

### ApiManager

`ApiManager` instance offers properties for each resource types: `.forms`, `.records`, `.projects`, `.photos`, `.videos`, `.audio`, `.signatures`. Each resource has following methods:

 * `.get(obj_id, cached=True)`
 * `.list(cached=True, url_params=None, use_generator=True, ignore_existing=False)`
 * `.remove(obj_id)`
 * `.list_removed()`


Sample usage:

 * get list of photos for given form from API

```
photos = api.photos.list(url_params={'form_id': FORM_ID}, cached=False)
```

 * get list of photos that are not added to database yet (`ignore_existing=True` doesn't work with `cached=True` flag set).

```
new_photos = api.photos.list(cached=False, ignore_existing=True)
```

 * get list of all stored forms:

```
forms = api.forms.list()
```

 * get list of all records stored for a form:

```
records = api.records.list(url_params={'form_id': FORM_ID})
```

 * remove specific record from local data:

```
removed_record = api.records.remove(RECORD_ID)
```


#### Resource classes

`ApiManager`'s resources methods returns approperiate resource class (Project, Form, Record, Media) or iterable (list, generator or Query, depending on input parameters) of resource classes.

Each resource class exposes common interface. See `pyfulcrum.lib.models` source for details. Most important elements of BaseResource class (and subclasses) are:
 
 * classmethod `.get(id, session)` retrives object by id (or returns `None` if it doesn't exist)
 * classmethod `.from_payload(payload, session, client, storage)` creates/updates object from JSON payload from Fulcrum API. 
 * instancemethod `.delete(session)` will mark object as removed.
 * `Record.get_values()` returns dictionary with values for given record with media resolved to local files. 

**Note:** that if any value in `Record` is media field and media it's refering is missing, field will return empty value. This is because data comming from Fulcrum API may not be entirely consistent (i.e. media resources may refer records that are not available in API for current user).

## PyFulcrum CLI

PyFulcrum provides simple cli interface to fetch and access data. Access can be in various formats:

 * str - plain string dump of basic object data, works with all resource types
 * csv - dumps payload keys as columns and values as rows, works with all resource types
 * raw - dumps raw payload for objects, works with all resource types
 * json - dumps basic data about objects, works with all resources
 * geojson - dumps payload data as properties, works with records only, will return records with points attached
 * shapefile - dumps payload data as properties, works with records only, will return records with points attached
 * kml - dumps payload data as properties, works with records only, will return records with points attached

CLI interface is available through `pyfulcrum` command (usually resides in `venv/bin/` directory). Invocation requires few mandatory params provided:

 * Fulcrum API key
 * database URL
 * root path to storage
 * (optional) url root for storage webserver
 * (optional) output format
 * (optional) output file to which results shoudl be written

Usage syntax and common parameters used by `pyfulcrum`:

```
usage: pyfulcrum [--version] [-v | -q] [--log-file LOG_FILE] [-h] [--debug]
                 --dburl DBURL --apikey APIKEY --storage STORAGE
                 [--urlbase URLBASE] [--format FORMAT] [--output OUTPUT]

  --dburl DBURL        database connection url
  --apikey APIKEY      Fulcrum API key
  --storage STORAGE    Storage directory root
  --urlbase URLBASE    Web root for storage
  --format FORMAT      Return format (default: json, available:
                       csv,geojson,json,kml,raw,shapefile,str). Mind that
                       spatial-aware formatters accept only record objects.
  --output OUTPUT      Name of output file, standard output as default
```

Example invocation:

```
venv/bin/pyfulcrum --dburl=postgres://user:pass@localhost/pyfulcrum --apikey=XXXXxxx --storage=/path/to/storage/ --urlbase=http://statics.server.com/ ..(additional args here)..
```

To avoid typing commands, you can create shell script wrapper, which will provide required configuration. There's sample script, `lib/examples/scripts/runfulcrum.sh`, which requires environment file (simple KEY=VALUE in each line) with configuration. Sample environment file:

```
DB_URL=postgresql://pyfulcrum:pyfulcrum@localhost/pyfulcrum
TEST_DB_URL=postgresql://pyfulcrum:pyfulcrum@localhost/pyfulcrum_test
API_KEY=XXXXXxxxxxxxXXXXXxxxxxxxxXXXXXxxxxxx
STORAGE_ROOT=/path/to/storage/
```

You should adjust values and paths in your environment file and `runfulcrum.sh` script to match your deployment.

### Available management commands

`pyfulcrum` command offers several commands that allow to list multiple, retrieve and remove one specific resource. 


#### List:

```
usage: pyfulcrum list [-h] [--cached] [--urlparams URLPARAMS [URLPARAMS ...]]
                      [--ignore-existing]
                      resource

List resources

positional arguments:
  resource              Name of resource to list (projects, forms, records,
                        values, media)

optional arguments:
  -h, --help            show this help message and exit
  --cached              Should app fetch data from live API
  --urlparams URLPARAMS [URLPARAMS ...]
                        list of name=value pairs of url params to pass to list
  --ignore-existing     Should app fetch only data that are not in local
                        database
```

Sample invocations:

* list all forms available from API (they will be fetched and saved in db):

```
./runfulcrum.sh list forms
```

* list all forms available stored in db:

```
./runfulcrum.sh list forms --cached
```

* list all forms available in API but not in db:

```
./runfulcrum.sh list forms --ignore-existing
```

* list all records in shapefile format with output to file

```
./runfulcrum.sh list records --cached --format shapefile --output records.shp.zip
```


`--urlparams URLPARAMS` param is a way to provide filtering query for both API call and cached resources. This is interpreted per-resource type, so forms can have different url params than records. Multiple params are allowed, as a list of params separated with space, i.e.: `--urlparams param1=value param2=othervalue`. In case of multiple params, they're used with operator `AND`.

Below is a list of resources and accepted url params:

 Resource type | URL params | meaning 
 --- | --- | --- 
 `forms` | `form_id` | filter list to show only form with specific id. equivalent of `get` command 
 `records` | `form_id` | Get records only ones related to specific form 
 | | `created_before` |  Return records that were created before specific timestamp 
 | | `created_since` | Returns records that were created from timestamp to now 
 | | `updated_before` | Returns records updated before specific timestamp 
 | | `updated_since` | Returns records updated after specific timestamp 

#### Get:

```
usage: pyfulcrum get [-h] [--cached] resource id

Shows single resource

positional arguments:
  resource    Name of resource to list (projects, forms, records, values,
              media)
  id          ID of resource to get

optional arguments:
  -h, --help  show this help message and exit
  --cached    Should app fetch data from live API

```

Sample invocations:

* Get specific form cached, with str (simple) format

```
$ ./runfulcrum.sh get forms dd7449cc-ef64-456f-9dc5-f2eca4afc07d --cached --format str
 
Form: id=dd7449cc-ef64-456f-9dc5-f2eca4afc07d name=test app records_count=4
```

* Get record in geojson format:

```
$ ./runfulcrum.sh get records b3d2e4dc-545c-4ebd-a53a-a6be7bad0dfb --cached --format geojson
{"type": "Feature", "id": "b3d2e4dc-545c-4ebd-a53a-a6be7bad0dfb", "geometry": {"type": "Point", "coordinates": [30.9502958, 20.2896016]}, "properties": {"deweeee": {"key": "0f50", "description": null, "label": "deweeee", "type": "TextField", "value": "Hdhj", "media": []}, "eeeee": {"key": "c2aa", "description": null, "label": "eeeee", "type": "YesNoField", "value": "yes", "media": []}, "ewrewerw": {"key": "aeb7", "description": null, "label": "ewrewerw", "type": "TextField", "value": "8688", "media": []}, "qwqwq": {"key": "4e91", "description": null, "label": "qwqwq", "type": "ChoiceField", "value": {"other_values": [], "choice_values": ["cccc", "ddd"]}, "media": []}, "Photos": {"key": "ac03", "description": null, "label": "Photos", "type": "PhotoField", "value": [{"photo_id": "05e61326-9046-4df4-9478-40e94b10414e", "caption": null}], "media": [{"id": "05e61326-9046-4df4-9478-40e94b10414e", "caption": null, "type": "photo", "paths": {"large": {"path": "/storage/dd7449cc-ef64-456f-9dc5-f2eca4afc07d/b3d2e4dc-545c-4ebd-a53a-a6be7bad0dfb/photo_large", "url": null}, "thumbnail": {"path": "/storage/dd7449cc-ef64-456f-9dc5-f2eca4afc07d/b3d2e4dc-545c-4ebd-a53a-a6be7bad0dfb/photo_thumbnail", "url": null}, "original": {"path": "/storage/dd7449cc-ef64-456f-9dc5-f2eca4afc07d/b3d2e4dc-545c-4ebd-a53a-a6be7bad0dfb/photo_original", "url": null}}}]}, "id": "b3d2e4dc-545c-4ebd-a53a-a6be7bad0dfb"}}
```

#### Remove:

```
usage: pyfulcrum remove [-h] [--cached] resource id

Removes resource from local data (this doesn't update state in Fulcrum API)

positional arguments:
  resource    Name of resource to list (projects, forms, records, values,
              media)
  id          ID of resource to get
```

Sample invocations:

 * remove specific record from local dataset
```
./runfulcrum.sh remove records 29ac7df1-69e8-4227-bb1c-9040196d3d4c
```

#### List removed

```
usage: pyfulcrum listremoved [-h] [--cached]
                             [--urlparams URLPARAMS [URLPARAMS ...]]
                             resource

List locally removed resources

positional arguments:
  resource              Name of resource to list (projects, forms, records,
                        values, media)
```

Sample invocations:

 * list removed records
```
$ ./runfulcrum.sh listremoved records --format str

Record: id=29ac7df1-69e8-4227-bb1c-9040196d3d4c status=fff form_id=dd7449cc-ef64-456f-9dc5-f2eca4afc07d
 field deweeee TextField: deweeee
   value: Vddy
 field eeeee YesNoField: eeeee
   value: yes
 field ewrewerw TextField: ewrewerw
   value: 568
 field qwqwq ChoiceField: qwqwq
   value: {'other_values': [], 'choice_values': ['cccc', 'ddd']}
```

## Storage

Storage handling is fairly simple. What is needed is a dedicated directory, to which files will be written. Optionally, storage can be exposed by http server, then you need to provide urlbase under which static files will be served.

Files are stored from the root of storage, in following path template: `${form_id}/${media_id}/${media_type}_${media_size}`. 

`media_type` is a name of media, can be one of: `video`, `photo`, `audio` or `signature`.

`media_size` is name of size for processed file. Each media file comes in several sizes, like several types of thumbnails. Depending on type of resource, sizes list can vary, but each media type has at least `original` size. Below is a list of media types and list of media sizes:


 | Media type  | Media size |
 | ----------- | ---------- |
 | `video`     | `thumbnail_small`, `thumbnail_medium`, |
 |             | `thumbnail_large`, `thumbnail_huge`, |
 |             | `thumbnail_small_square`, |
 |             | `thumbnail_medium_square`, |
 |             | `thumbnail_large_square`, |
 |             | `thumbnail_huge_square`, |
 |             | `small`, `medium`, |
 |             | `original` |
 | `photo`     | `large`, `thumbnail`, `original` |
 | `signature` | `large`, `thumbnail`, `original` |
 | `audio`     | `small`, `medium`, `original` |

Because multiple versions of media files are stored, it's important to provide sufficient amount of free space for storage.


## Notes
