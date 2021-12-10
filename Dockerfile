FROM python:3.11-rc-alpine

WORKDIR /app
COPY . .

RUN pip3 install flask --proxy http://proxy-do.smn.gov.ar:8080


ENTRYPOINT ["python3"]
