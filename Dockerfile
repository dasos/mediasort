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

EXPOSE 8080

ENTRYPOINT gunicorn mediasort_web:app --bind 0.0.0.0:8080 --log-level=debug --workers=1