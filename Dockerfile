# syntax=docker/dockerfile:1

FROM python:3.8-slim-buster

WORKDIR /usr/src/app

# install python lib requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy dir
COPY lidarcontroller/ ./lidarcontroller/
COPY static/ ./static/
COPY templates/ ./templates/
COPY utils/ ./utils/

# copy files
COPY config.py .
COPY run.py .
COPY .env .

# proxy
#ENV http_proxy=http://proxy-do.smn.gov.ar:8080
#ENV https_proxy=http://proxy-do.smn.gov.ar:8080

EXPOSE 5000
CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
