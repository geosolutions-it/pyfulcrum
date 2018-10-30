#!/bin/bash
set -e
set -x

echo "This is travis-build.bash..."

# remove faulty mongodb repo, we don't use it anyway
sudo rm -f /etc/apt/sources.list.d/mongodb-3.2.list
sudo add-apt-repository --remove 'http://us-central1.gce.archive.ubuntu.com/ubuntu/ main restricted'
sudo add-apt-repository --remove 'http://us-central1.gce.archive.ubuntu.com/ubuntu/ universe'
sudo add-apt-repository --remove 'http://us-central1.gce.archive.ubuntu.com/ubuntu/ multiverse'
sudo add-apt-repository 'http://archive.ubuntu.com/ubuntu/'
sudo add-apt-repository 'http://archive.ubuntu.com/ubuntu/ universe'
sudo add-apt-repository 'http://archive.ubuntu.com/ubuntu/ multiverse'
sudo apt-get -qq --fix-missing update
sudo apt-get install gdal-bin libgdal-dev python3-dev aptitude python3-pip python3-wheel

# PostGIS 2.1 already installed on Travis
cd lib

python3 -m venv --system-site-packages venv
VENV=venv/bin/
${VENV}pip install --upgrade pip
${VENV}pip install pygdal==$(gdal-config --version)
${VENV}pip install -r requirements.txt
${VENV}pip install -e .

cd -
sudo -u postgres -c "create role pyfulcrum superuser login password 'pyfulcrum';"
sudo -u postgres -c "create database pyfulcrum_test owner pyfulcrum;"
sudo -u postgres pyfulcrum -c 'create extension postgis;'

echo "travis-build.bash is done."
