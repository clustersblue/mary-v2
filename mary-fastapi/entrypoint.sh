#!/bin/sh
# Start as root so a freshly mounted storage volume can be given to the app
# user, then drop privileges before Uvicorn runs.
set -eu
mkdir -p /app/storage
chown -R app:app /app/storage
exec gosu app "$@"
