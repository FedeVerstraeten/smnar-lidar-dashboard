FROM python:3

WORKDIR /usr/src/app

COPY lidarcontroller/ ./lidarcontroller/
COPY static/ ./static/
COPY templates/ ./templates/
COPY utils/ ./utils/

COPY requirements.txt .
COPY config.py .
COPY run.py .

ENV http_proxy=http://proxy-do.smn.gov.ar:8080
ENV https_proxy=http://proxy-do.smn.gov.ar:8080

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python", "run.py"]
