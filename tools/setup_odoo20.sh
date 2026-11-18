#!/bin/bash
# Odoo 20 Community for projet_ocd in /opt/odoo20 (source, venv, odoo.conf), PostgreSQL, wkhtmltopdf, ffmpeg.
#
# The setup script of the cloud environment « projet_ocd » (claude.ai, Settings › Environments) runs
# these steps, as root, at the start of each new session, from the folder that holds the checkout;
# change both together. By hand: `bash tools/setup_odoo20.sh` (as root), from anywhere.
# Each step is skipped when it is done already: the script can run again without harm.
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
apt-get install -y wkhtmltopdf ffmpeg || (apt-get update -q && apt-get install -y wkhtmltopdf ffmpeg)
mkdir -p /opt/odoo20/data
[ -d /opt/odoo20/src ] || git clone --depth 1 --branch 20.0 https://github.com/odoo/odoo.git /opt/odoo20/src
[ -d /opt/odoo20/venv ] || python3 -m venv /opt/odoo20/venv
/opt/odoo20/venv/bin/pip install -q --upgrade pip wheel setuptools
# python-ldap needs the headers of OpenLDAP (not used by OCD Live); psycopg2 in its binary wheel
grep -v "python-ldap" /opt/odoo20/src/requirements.txt | sed 's/^psycopg2==/psycopg2-binary==/' > /opt/odoo20/requirements-ocd.txt
/opt/odoo20/venv/bin/pip install -q -r /opt/odoo20/requirements-ocd.txt -r "$REPO/requirements.txt"
service postgresql start
# Odoo runs as root here: a role of PostgreSQL of the same name, through the local socket
su postgres -c "psql -tAc \"select 1 from pg_roles where rolname = 'root'\"" | grep -q 1 \
  || su postgres -c "psql -c 'create role root superuser login'"
if [ ! -f /opt/odoo20/odoo.conf ]; then
  cat > /opt/odoo20/odoo.conf <<CONF
[options]
addons_path = /opt/odoo20/src/addons,/opt/odoo20/src/odoo/addons,$REPO/marketplace/oca_server_brand,$REPO
data_dir = /opt/odoo20/data
admin_passwd = admin
CONF
fi
/opt/odoo20/venv/bin/python /opt/odoo20/src/odoo-bin --version
