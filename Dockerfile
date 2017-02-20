FROM ubuntu:latest
MAINTAINER Joel Pitt "joel@joelpitt.com"

RUN apt-get update -y
RUN apt-get install -y python-pip python-dev build-essential

COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt

CMD ["python", "safetycheck.py"]