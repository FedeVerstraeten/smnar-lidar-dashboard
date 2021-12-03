# Runing Python from Zip packages

## Project dependencies

Previously, you have to create a list of dependencies using `pipreqs` (alternative can be` pip freeze`):

```
pipreqs my-zipped-project/
```
The `requirements.txt` file contain a list of libraries necessary to execute the project will be created in  `my-zipped-project/` directory.

Downloading libraries:

```
python3 -m pip install -r my-zipped-project/requirements.txt  --target my-zipped-project/packages/
```


## How to make an executable using `zipapp`

- Install the dependencies listed in the file requirements

- Create a zip file from the project directory:

```
python3 -m zipapp -p "/usr/bin/env python3" my-zipped-project/
```

- Running from the zip file (on Linux/Ubuntu):

```
./my-zipped-project.pyz
```

- **TO-DO:** Create a symlink to run the executable zip file.

## Create executable from a zip file

- Create the zip file with the project code, adding a *shebang* to run with **Python 3**:

```
zip my-zipped-project.zip my-zipped-project/*
echo '#!/usr/bin/env python3' | cat - my-zipped-project.zip > my-zipped-project
chmod 755 my-zipped-project.exe
```

- Then, you can run using the command `python` or `python3`

```
python3 my-zipped-project
```

- or directly like a native program.

```
./my-zipped-project
```