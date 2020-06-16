# placement-exams

Designed to support University of Michigan placement exams administered through the Canvas LMS,
the in-development placement-exams application will collect the students' scores from multiple exams
and send them to M-Pathways so the registrar can grant course enrollment privileges. The UM API Directory
will be used both to access the Canvas API and send scores to M-Pathways.

## Development

### Pre-requisities

The sections below provide instructions for configuring, installing, using, and changing 
the application. Depending on the environment you plan to run the application in, you may 
also need to install some or all of the following:

* [Python 3.8](https://docs.python.org/3/)
* [MySQL](https://dev.mysql.com/doc/)
* [Docker Desktop](https://www.docker.com/products/docker-desktop)
* [OpenShift CLI](https://docs.openshift.com/enterprise/3.1/cli_reference/get_started_cli.html)

While performing any of the actions described below, use a terminal, text editor, or file
utility as necessary. Some sample command-line instructions are provided for some steps.

### Configuration

Before running the application, you will need to prepare two configuration-related files:
a `.env` file containing key-value pairs that will be added to the environment, and
a `fixtures.json` file containing report and exam records that will initialize data in the database
and determine for which exams submission data is collected and sent to M-Pathways.
Both files are described in more detail below. See the **Installation & Usage** section below for details
on where these files will need to be located.

* `.env`

  The `.env` file serves as the primary configuration file, loading credentials for accessing
  the application's database and the UM API Directory. A template called `.env.sample` has been provided in
  the `config` directory. The comments before the variables in the template should describe the purpose of
  each; some recommended values have been provided. If you use the approach described below
  in **Installation & Usage - With Docker**, you can use the provided values to connect to the database
  managed by Docker.

* `fixtures.json`

  The `fixtures.json` file allows users to pre-populate the database with records for exams and reports
  on submissions processed. The JSON file uses the Django model instance
  [serialization format](https://docs.djangoproject.com/en/3.0/topics/serialization/#serialization-formats-json),
  and records are loaded using Django's
  [`loaddata` management command](https://docs.djangoproject.com/en/3.0/ref/django-admin/#loaddata).
  
  The file should contain data for one or many `Report` records and one or many `Exam` records
  connected to a previously defined `Report` by ID number. For an example, take a look `sample_fixtures.json`
  in the `config` directory. While `Submission` records can also be imported using fixtures, the application
  will handle creation of all these records.

Create your own versions of `.env` and `fixtures.json`, and be prepared to move them to specific directories.

### Installation & Usage

#### With Docker

This project provides a `docker-compose.yaml` file to help simplify the development and testing process. 
Invoking `docker-compose` will set up MySQL and a database in a container. 
It will then create a separate container for the job, which will interact with the MySQL container's database,
inserting and updating submission records.

Before beginning, perform the following additional steps to configure the project for Docker.

1. Create one path in your home directory (i.e., `~` or `${HOME}`): `secrets/placement-exams`

    The `docker-compose.yaml` file specifies that there should be a mapping between 
    the `secrets/placement-exams` directory and the repository's `config/secrets` directory.
    In other words, files you place in `secrets/placement-exams` will be available to the application
    in the repository at `config/secrets`.

2. Place the `.env` and `fixtures.json` files described in **Configuration** above in `~/secrets/placement-exams`.

Once these steps are completed, you can use the standard `docker-compose` commands to build and run the application.

1. Build the images for the `mysql` and `job` services.

    ```sh
    docker-compose build
    ```

2. Start up the services.

    ```sh
    docker-compose up
    ```

`docker-compose-up` will first start the MySQL container and then the job container. 
When the job finishes, the job container will stop, but the MySQL container will continue running.
This allows you to enter the container and execute queries (or connect to the database via other utilities).

```sh
docker exec -it placement_exams_mysql /bin/bash
mysql --user=pe_user --password=pe_pw
```

Use `^C` to stop the running MySQL container,
or -- if you used the detached flag `-d` with `docker-compose up` -- use `docker-compose down`.

Data in the MySQL database will persist after the container is stopped.
The MySQL data is stored in a volume mapped to the `.data/` directory in the project.
To completely reset the database, delete the `.data` directory.

To run the test suite using `docker-compose`, use the following command, which sets up an environment variable
checked by the `start.sh` script (the entrypoint for Docker).

```sh
docker-compose run -e TEST_MODE=True job
```

#### With a Virtual Environment

You can also set up the application using `virtualenv` by doing the following:

1. Set up a MySQL database for the application using a MySQL installation on your local machine.
   
   Ensure that you have placed the database credentials in your `.env` file

2. Place your `.env` and `fixtures.json` files in `config/secrets`.

3. Create a virtual environment using `virtualenv`.

    ```sh
    virtualenv venv
    source venv/bin/activate  # for Mac OS
    ```

4. Install the dependencies specified in `requirements.txt`.

    ```sh
    pip install -r requirements.txt
    ```

5. Run the application.

    ```sh
    python entry.py
    ```

To run the test suite, use the following commands:

  ```sh
  # New tests
  python manage.py test -v 3
  # Previous tests
  python -m unittest test/spe_test.py
  ```

(*I'm going to worry about updating the below sections later.* - Sam)

### Openshift setup
1. login to openshift from command line
2. `oc new-project <name-you-like>`
3. creating a new bash app for storing `persisted.txt` file `oc new-app --docker-image=bash` and configure it to run 
    unconditionally add a persistent storage
   and mount the volumn on bash pod
4. creating a new app from a git branch `oc new-app https://github.com/<user>/spanish-placement-exam-python#i3_dockerizing_spe`
    a. link the persisted.txt to this pod
5. Using Openshift [cronJob](https://docs.openshift.com/container-platform/3.10/dev_guide/cron_jobs.html) feature to run the SPE process.
6. starting the cron run as `oc create -f cron_spe_test.yml`. You can download the file from the [Box Folder](https://umich.app.box.com/folder/67252746472) for respective env
7. Looking at the cron job in openshift instance `oc get cronjobs`
8. For deleting cron jobs `oc delete cronjob/cron1` (beware we have only once instance that holds both dev/prod instance)

### Sending email
Running a local SMTP debugging server. Rather than sending emails to the specified address, 
it discards them and prints their content to the console.
1. 'python -m smtpd -d -n -c DebuggingServer localhost:1025 &'
