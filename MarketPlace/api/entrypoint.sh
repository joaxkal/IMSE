#!/bin/sh

echo "Waiting for POSTGRESQL..."

sleep 1

echo "POSTGRESQL started"


python /app/fill_db.py

python /app/run.py

exec "$@"