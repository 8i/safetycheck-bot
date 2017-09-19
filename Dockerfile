FROM ubuntu:xenial
MAINTAINER Joel Pitt "joel@joelpitt.com"

RUN apt-get update && \
  apt-get -y dist-upgrade && \
  apt-get clean && \
  apt-get install -y jq python-dev python-pip build-essential && \
  rm -rf /var/lib/apt/lists/*

ENV AWS_DEFAULT_REGION=us-west-2
RUN pip install awscli && \
  curl -sL https://gist.github.com/rafaelmagu/782e1a6e3e1e70799e38682f9cf069e1/raw/065a6de34b1e42ec1229ab00cd09c684e4662304/ssm-params-to-env.sh > /usr/local/bin/ssm-params-to-env.sh && \
  chmod +x /usr/local/bin/ssm-params-to-env.sh

COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt

CMD ["python", "safetycheck.py"]
