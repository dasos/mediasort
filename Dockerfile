#FROM ubuntu

#EXPOSE 5000

#RUN apt-get update -qq \
#    && DEBIAN_FRONTEND="noninteractive" apt-get -y install exiftool python3 python3-flask python3-dateutil python3-opencv python3-exifread --no-install-recommends

#COPY . /photosort/

#ENV FLASK_APP=/photosort/photosort-web

#ENTRYPOINT flask run --host=0.0.0.0 



FROM jjanzic/docker-python3-opencv

RUN apt-get update -qq \
    && apt-get -y --no-install-recommends install exiftool \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get -qq autoremove \
    && apt-get -qq clean

WORKDIR /usr/src/mediasort

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


COPY . ./

ENV FLASK_APP=./mediasort-web

EXPOSE 5000

ENTRYPOINT flask run --host=0.0.0.0 
