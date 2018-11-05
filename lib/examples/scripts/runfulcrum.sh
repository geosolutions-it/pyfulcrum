#!/bin/bash

THIS_DIR=$(dirname $0)
COMMON_PREFIX=~/work/pyfulcrum-dev/
ENV_FILE="${COMMON_PREFIX}conf/env"
VENV_BIN_DIR="${COMMON_PREFIX}venv/bin"
PYTHON=${VENV_BIN_DIR}/python
PYFULCRUM=${VENV_BIN_DIR}/pyfulcrum

while read -r line
do
 export $(echo "$line")
done < $ENV_FILE


cd $(dirname 0)
$PYFULCRUM --dburl=${DB_URL} --apikey=${API_KEY} --storage=${STORAGE_ROOT} $@
