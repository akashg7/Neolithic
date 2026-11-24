#!/bin/sh
# API container start: initialise the DB on first boot, then serve.
set -e
python -m scripts.bootstrap_db
exec "$@"
