#!/bin/sh
set -e

if [ "$RUN_INIT" = "1" ]; then
    echo "Running migrations..."
    python manage.py migrate --noinput

    echo "Compiling translation messages..."
    python manage.py compilemessages || true

    echo "Generating favicon from brand logo..."
    python manage.py generate_favicon || true

    echo "Collecting static files..."
    python manage.py collectstatic --noinput
fi

exec "$@"
