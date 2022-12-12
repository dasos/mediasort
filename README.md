# mediasort

MediaSort is a Python3 web UI that helps you sort media items into folders. The classic use case is to take the many photos and videos produced by a smartphone, and makes sense of them. It also works well for a DSLR.

## Dependancies
Python 3, plus the modules in requirements.txt

Note you should also have exiftool installed seperately. If you do not, fewer files will be processed - and tests will fail!

The minimum version of exiftool is 12.15. If the correct version is not installed, it will fail silently. (Not sure why...)

For Ubuntu, the minimum version is in 22.04 (jammy) and later. You can download the [package](https://packages.ubuntu.com/jammy/all/libimage-exiftool-perl/download) directly and install it on earlier versions.

## How to run a development server
Assumption is a Ubuntu machine

Install the dependanices (exiftool may need some help)

    pip3 install -r requirements.txt
	sudo apt install exiftool

Set the variables

    export FLASK_REDIS_URL="redis://<ip>:<port>/0"
    export FLASK_ENV=development

Execute

    python3 -m flask --app web_app run

or to have it listen across the network:

    python3 -m flask --app web_app run --host=0.0.0.0

## How to test

pytest is used. Invoke:

    python3 -m pytest

Coverage (and a nice HTML report) is determined:

    python3 -m pytest --cov . --cov-branch --cov-report html