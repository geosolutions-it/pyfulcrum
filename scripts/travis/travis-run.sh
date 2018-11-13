#!/bin/sh -e

# echo "NO_START=0\nJETTY_HOST=127.0.0.1\nJETTY_PORT=8983\nJAVA_HOME=$JAVA_HOME" | sudo tee /etc/default/jetty
# sudo cp ckan/ckan/config/solr/schema.xml /etc/solr/conf/schema.xml
# sudo service jetty restart
set -x
set -e
TEST_DB_URI=postgresql://pyfulcrum:pyfulcrum@localhost/pyfulcrum_test pytest  --cov=pyfulcrum.lib --cov=pyfulcrum.web $@
