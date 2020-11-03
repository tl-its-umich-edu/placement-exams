# placement-exams

Designed to support University of Michigan placement exams administered through the Canvas LMS,
the placement-exams application collects students' scores for multiple exams
and sends them to M-Pathways so the registrar can grant course enrollment privileges. The UM API Directory
is used both to access the Canvas API and send scores to M-Pathways.

## Development

### Pre-requisities

The sections below provide instructions for configuring, installing, and using the application.
Depending on the environment you plan to run the application in, you may
also need to install some or all of the following:

*   [Python 3.8](https://docs.python.org/3/)
*   [MySQL](https://dev.mysql.com/doc/)
*   [Docker Desktop](https://www.docker.com/products/docker-desktop)
*   [OpenShift CLI](https://docs.openshift.com/enterprise/3.1/cli_reference/get_started_cli.html)

While performing any of the actions described below, use a terminal, text editor, or file
utility as necessary. Sample terminal commands are provided for some steps.

### Configuration

Before running the application, you will need to prepare two configuration-related files:
a `.env` file containing key-value pairs that will be added to the environment, and
a `fixtures.json` file containing report and exam records that will initialize data in the database
and determine for which exams submission data is collected and sent to M-Pathways.
Both files are described in more detail below. See the **Installation & Usage** section below for details
on where these files will need to be located.

*   `.env`

    The `.env` file serves as the primary configuration file, loading credentials for accessing
    the application's database and the UM API Directory. A template called `.env.sample` has been provided in
    the `config` directory. The comments before the variables in the template should describe the purpose of
    each; some recommended values have been provided. If you use the approach described below
    in **Installation & Usage - With Docker**, you can use the provided values to connect to the database
    managed by Docker.

*   `fixtures.json`

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

1.  Create one path in your home directory (i.e., `~` or `${HOME}`): `secrets/placement-exams`

    The `docker-compose.yaml` file specifies that there should be a mapping between 
    the `secrets/placement-exams` directory and the repository's `config/secrets` directory.
    In other words, files you place in `secrets/placement-exams` will be available to the application
    in the repository at `config/secrets`.

2.  Place the `.env` and `fixtures.json` files described in **Configuration** above in `~/secrets/placement-exams`.

Once these steps are completed, you can use the standard `docker-compose` commands to build and run the application.

1.  Build the images for the `mysql` and `job` services.

    ```sh
    docker-compose build
    ```

2.  Start up the services.

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

1.  Set up a MySQL database for the application using a MySQL installation on your local machine.
   
    Ensure that you have placed the database credentials in your `.env` file.

2.  Place your `.env` and `fixtures.json` files in the `config/secrets` directory within the project.

3.  Create a virtual environment using `virtualenv`.

    ```sh
    virtualenv venv
    source venv/bin/activate  # for Mac OS
    ```

4.  Install the dependencies specified in `requirements.txt`.

    ```sh
    pip install -r requirements.txt
    ```

5. Prepare the database by running migrations and loading your fixtures.

    ```sh
    python manage.py migrate
    python manage.py loaddata fixtures.json
    ```

6. Run the application.

    ```sh
    python manage.py run
    ```

To run the test suite, use the following commands:

```sh
coverage run manage.py test -v 3
coverage report
```

#### Sending email

The application sends emails reporting on the results of its runs. The process defaults to sending email
instead to the console, using
[one of Django's dummy email backends](https://docs.djangoproject.com/en/3.0/topics/email/#console-backend).
To configure the application to actually send email, in `.env`, ensure `EMAIL_DEBUG` is set to `0` and that
you have provided `SMTP_PORT` and `SMTP_HOST` values pointing to a SMTP server accessible from your host
(see **Configuration** above).

### Deployment: OpenShift

Deploying the application as a job using OpenShift and Jenkins involves several steps that are beyond the scope of
this README. However, some details about how the job is configured are provided below.

The files described in the **Configuration** section above need to be made available to running placement-exams
containers as [OpenShift Secrets](https://docs.openshift.com/container-platform/3.7/dev_guide/secrets.html).
A volume containing versions of `.env` and `fixtures.json` should be mapped to a configuration directory,
typically `config/secrets`. These details will be specified in a YAML configuration file defining the pod. 

In OpenShift, some application settings are controlled by specifying environment variables in the pod
configuration file. More details on these environment variables -- and whether they are optional or required --
are provided below.

*   `ENV_DIR` (Optional): By default, the application will expect to find the files described in **Configuration**
    within the `config/secrets` sub-directory. However, this location can be changed by setting `ENV_DIR` to the
    desired path. To avoid problems during volume mapping, the specified directory should not contain any files
    needed by the application. Using `config/secrets` is currently recommended.

*   `ENV_FILE` (Optional): By default, the application will expect the main configuration file to be named `.env`.
    However, this name can be changed by setting `ENV_FILE` to the desired name. This can be useful when maintaining
    multiple versions of the configuration file, e.g. `test.env` or `prod.env`.

*   `FIXTURES_FILE` (Required): When the `start.sh` script loads fixture data, it references the `FIXTURES_FILE`
    environment variable; thus, this variable **must** be set in the pod configuration. While using the
    `fixtures.json` name employed by `docker-compose` for local development is acceptable, this variable can
    also be used to change the file name as desired.

When setting all the above variables, the `env` block in the YAML file will look something like this:

```yaml
- env:
  - name: ENV_DIR
    value: /config/secrets
  - name: ENV_FILE
    value: test.env
  - name: FIXTURES_FILE
    value: some_fixtures.json
```
