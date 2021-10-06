# Commands step-by-step to create mypython-website

How to create a basic website using Flask Python framework and deploy tu "production" with Heroku.

## Basic Flask

Flask instalation:

```bash
$ pip3 install flask
```

Run webserver manually (for each code update):
```bash
$ python3 index.py 
 * Serving Flask app 'index' (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: off
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
```

Make a new directory with HTML templates:
```bash
$ mkdir templates

```

Python3 with Flask on debug mode
```bash
$ python3 index.py
 * Serving Flask app 'index' (lazy loading)
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: on
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 705-797-471
```

Make a new directory for CSS and JS files (styles):
```bash
$ mkdir static/ #styles is other option
$ mkdir static/css/
```

Move all file to src dir
```bash
$ mkdir src/ 
$ mv * src/ 
```

Install virtualenv for python.
```bash
# with pip
$ pip install virtualenv

# or

# On Debian/Ubuntu systems, you need to install the python3-venv
# package using the following command.
$ sudo apt install python3.8-venv
```

Create a virtual enviroment for python project:
```bash
python3 -m venv venv
```

Download and install Flask into virtual env using pip3
```bash
$ venv/bin/pip3 install flask

```

The Heroku deploy needs: the `requiments.txt` file with the package names, the `runtime.txt` file with the Python version, the **Procfile** that specifies the startup sequence and a plugin called `gunicorn`.

Install Gunicorn plugin to run a HTTP Server for UNIX.
```bash
$ venv/bin/pip3 install gunicorn
```

and then add the startup sequence in Procfile.
```bash
$ vim src/Procfile
$ cat src/Procfile 
web: gunicorn index:app # where index:app means <MY_MAIN_FILE>:<MY_MAIN_APP>
```

Specify the Python version on runtime file. By default, new Python application on Heroku use Python runtime `python-3.9.6` (from June 25, 2021).
```bash
$ python3 --version
Python 3.8.10
$ echo -n python-3.8.10 > ./src/runtime.txt
```

Create a requirements file with all the Python packages required by the web application. We should use `freeze` to list packages and module functions, but we can also use `pipreqs`. The command `freeze` must be run in venv mode.

Export the requirements list using freeze. Previously run the virtual enviroment.
```bash
$ . venv/bin/activate
$ pip freeze src/.
click==8.0.1
Flask==2.0.1
gunicorn==20.1.0
itsdangerous==2.0.1
Jinja2==3.0.1
MarkupSafe==2.0.1
Werkzeug==2.0.1
```

## Heroku

Sign up on the Heroku website if necessary.

Install Heroku client:
```bash
$ sudo snap install --classic heroku
$ heroku --version
 ›   Warning: heroku update available from 7.56.0 to 7.56.1.
heroku/7.56.0 linux-x64 node-v12.21.0

```

Heroku login:
```bash
$ heroku login
 ›   Warning: heroku update available from 7.56.0 to 7.56.1.
(node:23553) SyntaxError Plugin: heroku: /home/myuser/.local/share/heroku/config.json: Unexpected end of JSON input
module: @oclif/config@1.17.0
task: runHook prerun
plugin: heroku
root: /snap/heroku/4068
See more details with DEBUG=*
heroku: Press any key to open up the browser to login or q to exit: 
Opening browser to https://cli-auth.heroku.com/auth/cli/browser/1a9a5631-bf90-469a-8bb7-c9e776b82f90?requestor=SFMyNTY.g2gDbQAAAA0xNzkuMzcuMzkuMjM0bgYAKOO27noBYgABUYA.TjJnkLx7MVJiYRf4TxMIlDdLmf78ZWp-EgF6ua3fSog
Logging in... done
Logged in as myemail@gmail.com

```

Create a Git repository to link to Heroku:

```bash
$ cd src/
$ git init
$ git add .
$ git commit -m "First commit"
```

Create a Heroku app:
```bash
$ heroku create mypython-website
 ›   Warning: heroku update available from 7.56.0 to 7.56.1.
Creating ⬢ mypython-website... ⣾ 
(node:30533) SyntaxError Plugin: heroku: /home/myuser/.local/share/heroku/config.json: Unexpected end of JSON input
module: @oclif/config@1.17.0
task: runHook prerun
plugin: heroku
root: /snap/heroku/4068
Creating ⬢ mypython-website... done
https://mypython-website.herokuapp.com/ | https://git.heroku.com/mypython-website.git
```

and then push the Git repo to Heroku:
```bash
$ heroku git:remote mypython-website
...
set git remote heroku to https://git.heroku.com/mypython-website.git

$ git push heroku master # or main
...
...
remote: Verifying deploy... done.
To https://git.heroku.com/mypython-website.git
 * [new branch]      master -> master
```

another way to link the repository with Heroku (if the app name is already taken)
```bash
$ heroku create
...
...
Creating ⬢ another-python-website... done
https://another-python-website.herokuapp.com/ | https://git.heroku.com/another-python-website.git

$ heroku git:remote another-python-website
...
set git remote heroku to https://git.heroku.com/another-python-website.git

$ git push heroku master # or main
...
...
remote: Verifying deploy... done.
To https://git.heroku.com/another-python-website.git
 * [new branch]      master -> master
```

And finally you can check the deploy on [Heroku dashboard](https://dashboard.heroku.com/apps/mypython-website) and open the new website.
```bash
$ heroku open
```