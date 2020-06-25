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

echo 'Applying any outstanding migrations'
python manage.py migrate

python manage.py loaddata "$FIXTURES_FILE"

if [ "${TEST_MODE}" == "True" ]; then
    echo "Running tests"
    coverage run manage.py test -v 3
    coverage report
elif [ -z "${CRONTAB_SCHEDULE}" ]; then
    echo "CRONTAB_SCHEDULE environment variable was not set; a one-time job will be triggered"
    python entry.py
else
    # in cron pod
    echo Running cron job pod
    echo "CRONTAB_SCHEDULE is ${CRONTAB_SCHEDULE}"
    python -m smtpd -d -n -c DebuggingServer localhost:1025 &

    # Make the log file available
    touch /var/log/cron.log

    # Get the environment from docker saved
    # https://ypereirareis.github.io/blog/2016/02/29/docker-crontab-environment-variables/
    printenv | sed 's/^\([a-zA-Z0-9_]*\)=\(.*\)$/export \1="\2"/g' >> "$HOME"/.profile

    echo "${CRONTAB_SCHEDULE} . $HOME/.profile; python /spe/entry.py >> /var/log/cron.log 2>&1" | crontab
    crontab -l && cron -L 15 && tail -f /var/log/cron.log
fi
