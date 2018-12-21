### SPANISH PLACEMENT EXAM SCORE

The project is about getting the spanish placement exam scores that is taken by students by enrolling to a specific canvas
course and sending the to Mpathways. This project get grades from canvas using the CanvasAPI and send them to the Mpathway. API directory
is used in both cases for getting and sending the grades.

### Project Setup
1. create venv as `python3 -m venv <directory-to-spe-venv>` and activate the venv
2. In future will make use of the `api-util-package` install it by `git clone https://github.com/tl-its-umich-edu/api-utils-python`
 and do `pip install .`. this should get the api-utils in the site-packages 
3. `pip install -r requirements.txt`


Note: If you have lot of venv then it would be good that have a venv naming convention as `venv_spe, venv_xvg`
this way it will ignore the venv in the git commit and you have option to keep separate venv titled according to project