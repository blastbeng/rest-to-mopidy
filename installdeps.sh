#/bin/sh
/usr/bin/python3 -m venv .venv
source .venv/bin/activate; pip3 install wheel
source .venv/bin/activate; pip3 install -r requirements.txt
mkdir -p ./config
mkdir -p /run/user/1000/tmp/rest-to-tts
cp uwsgi.ini ./config/uwsgi.ini
