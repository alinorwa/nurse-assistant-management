#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

# انتظار قاعدة البيانات المحلية على جهازك
echo "Waiting for local postgres..."
while ! nc -z host.docker.internal 5432; do
  sleep 0.1
done
echo "Local PostgreSQL started"

exec "$@"