#!/bin/sh

echo "Waiting for MYSQL..."

sleep 1

echo "MySQL started"


python /app/fill_db.py

python /app/run.py

exec "$@"