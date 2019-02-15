# FROM directive instructing base image to build upon
FROM python:3.7

COPY requirements.txt /requirements.txt

ENV API_UTILS_VERSION v1.3
RUN git clone https://github.com/tl-its-umich-edu/api-utils-python && cd api-utils-python && git checkout tags/${API_UTILS_VERSION} && pip install .
RUN pip install -r /requirements.txt

# apt-utils needs to be installed separately
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-dev xmlsec1 cron && \
    apt-get clean -y

# COPY startup script into known file location in container
COPY start.sh /start.sh

WORKDIR /spe/
COPY . /spe/

# Sets the local timezone of the docker image
ENV TZ=America/Detroit
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

CMD["python", "entry.py"]