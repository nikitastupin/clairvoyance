#!/bin/sh

set -e

. /opt/pysetup/.venv/bin/activate

exec python3 -m clairvoyance "$@"
