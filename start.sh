#!/bin/bash

if [ "${HOW_STARTED}" == "DOCKER_COMPOSE" ]; then
    # Stolen from Matt Jones
    echo "Waiting for DB"
    while ! nc -z "${MYSQL_HOST}" "${MYSQL_PORT}"; do
        sleep 1 # Wait 1 second before checking again
    done

    echo "Creating new migration files based on model changes"
    python manage.py makemigrations
fi

echo "Applying any outstanding migrations"
python manage.py migrate

python manage.py loaddata "$FIXTURES_FILE"

if [ "${TEST_MODE}" == "True" ]; then
    echo "Running tests"
    coverage run manage.py test -v 3
    coverage report
else
    echo "Running main placement-exams process"
    python manage.py run
fi
