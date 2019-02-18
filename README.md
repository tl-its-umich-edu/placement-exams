# SPANISH PLACEMENT EXAM SCORE

The project is about getting the spanish placement exam scores that is taken by students by enrolling to a specific canvas
course and sending the to Mpathways. This project get grades from canvas using the CanvasAPI and send them to the Mpathway. API directory
is used in both cases for getting and sending the grades.

### Project Setup
1. create venv as `python3 -m venv <directory-to-spe-venv>`
  *activate as `source <path-to-venv>/bin/activate` 
  *be at the directory where you can see the `venv` enabled and from commandline type `deactivate'
2. In future will make use of the `api-util-package` install it by `git clone https://github.com/tl-its-umich-edu/api-utils-python`
 and do `pip install .`. this should get the api-utils in the site-packages 
3. `pip install -r requirements.txt`
4. run the script as `python entry.py`


### Docker run
1. Build the app `docker build -t <build-name> .` 
2. Run the app and providing the .env file from command line. `docker run --env-file .env -it --rm --name <run-name> <build-name>`

### Openshift setup
1. login to openshift from command line
2. `oc new-project <name-you-like>`
3. creating a new bash app for storing `persisted.txt` file `oc new-app --docker-image=bash` and add a persistent storage
   and mount the volumn on bash pod
4. creating a new app from a git branch `oc new-app https://github.com/pushyamig/spanish-placement-exam-python#i3_dockerizing_spe`
    a. link the persisted.txt to this pod
### Sending email
Running a local SMTP debugging server. Rather than sending emails to the specified address, 
it discards them and prints their content to the console.
1. python -m smtpd -d -n -c DebuggingServer localhost:1025 & 
