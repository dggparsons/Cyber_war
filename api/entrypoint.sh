#!/bin/sh
set -e

# Fix ownership of the mounted volume (runs as root before privilege drop).
# Docker named volumes start root-owned; appuser needs write access for
# the SQLite database and log files.
mkdir -p /app/instance/logs
chown -R appuser:appgroup /app/instance

# Drop to appuser and exec the CMD passed by Docker.
exec gosu appuser "$@"
