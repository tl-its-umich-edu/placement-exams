/* 
This script enables the user set up by docker-compose to perform MySQL actions required by
the Django test runner, i.e. create and manage a copy of the application database. The 
docker-compose.yml file maps the repository's mysql directory (and this file) into the MySQL
container at docker-entrypoint-initdb.d. All SQL files found in this directory will be run 
when the container first sets up the MySQL database. See the documentation links below
for more information.

Docker Hub - mysql: https://hub.docker.com/_/mysql
Django test databases: 
https://docs.djangoproject.com/en/3.0/topics/testing/overview/#the-test-database
*/

GRANT ALL PRIVILEGES ON *.* TO pe_user;