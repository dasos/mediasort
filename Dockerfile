FROM python:3.9

RUN apt-get update -qq \
    && apt-get -y --no-install-recommends install exiftool \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get -qq autoremove \
    && apt-get -qq clean

COPY --from=mwader/static-ffmpeg:6.0 /ffmpeg /usr/local/bin/
COPY --from=mwader/static-ffmpeg:6.0 /ffprobe /usr/local/bin/

WORKDIR /usr/src/mediasort

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

COPY images /input
RUN mkdir -p /config
VOLUME ["/config"]

ENV PYTHONUNBUFFERED=1

EXPOSE 8080

ENTRYPOINT gunicorn 'web_app:create_app()' --bind 0.0.0.0:8080 --workers=5
