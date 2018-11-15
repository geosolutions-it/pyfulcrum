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

1. Run tests with `TEST_DB_URL` env variable pointing to test database. Adjust variable contents to your deployment. `--cov` switch will generate code coverage statistics:

    ```
    TEST_DB_URL=postgresql://pyfulcrum:pyfulcrum@localhost/pyfulcrum_test venv/bin/pytest --cov=pyfulcrum.lib --cov=pyfulcrum.web
    ```
