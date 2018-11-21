# pyfulcrum

Python packages for Fulcrum Webhooks and Fulcrum forms backup.

contains:
 * `lib` dir - pyfulcrum models/api
 * `web` dir - pyfulcrum web apps


## PyFulcrum-lib

 PyFulcrum-lib is a database and access API layer to handle Fulcrum backup data.

 see [PyFulcrum-lib](lib/README.md) for details

## PyFulcrum-web 
 
 PyFulcrum-web is a pair of Flask blueprints: webhook recievier and simple web-based API to retrivie Fulcrum data stored locally.

 see [PyFulcrum-web](web/README.md) for details

## Data synchronization

While `PyFulcrum-web` provides webhook receiver, Fulcrum may not dispatch event for any reason. To have local data aligned, it's advised to set up cron job that will synchronize forms/records according to regular schedule. Sample crontab entries:

```
FULCRUMBIN=/pat/to/venv/bin/pyfulcrum --dburl=... --apikey=... --storage=...

1 * * * * $FULCRUMBIN list forms
2 * * * * $FULCRUMBIN list records

```

## Testing

Both packages contain test suite. Recommended way is to run those tests with `pytest`. Full installation procedure for test environment is:

1. Install both `PyFulcrum-lib` and `PyFulcrum-web` packages, accordingly to instructions in their Readme files.

1. Install test dependencies in `test-requirements.txt` for each package:

    ```
    venv/bin/pip install -r lib/test-requirements.txt
    venv/bin/pip install -r web/test-requirements.txt
    ```

1. Create test database with PostGIS extension:

    ```
    psql -U postgres -c 'create database pyfulcrum_test owner to pyfulcrum;'
    psql -U pyfulcrum -d pyfulcrum_test -c 'create extension postgis;'
    ```

1. Run tests with `TEST_DB_URL` env variable pointing to test database. Adjust variable contents to your deployment. `--cov` switch will generate code coverage statistics for both `web` and `lib`:

    ```
    TEST_DB_URL=postgresql://pyfulcrum:pyfulcrum@localhost/pyfulcrum_test venv/bin/pytest --cov=pyfulcrum.lib --cov=pyfulcrum.web
    ```

To run tests for specific package, you can point to code path (assuming you're running tests in root directory of repository):

    ```
    TEST_DB_URL=postgresql://pyfulcrum:pyfulcrum@localhost/pyfulcrum_test venv/bin/pytest lib/
    ```
