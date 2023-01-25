#!/usr/bin/env bash
mkdir -p ./config
mkdir -p /run/user/1000/tmp/rest-to-tts
cp uwsgi.ini ./config/uwsgi.ini
rm -f /run/user/1000/tmp/rest-to-tts/fakeyou_voices.sqlite
source .venv/bin/activate; uwsgi --ini ./config/uwsgi.ini --enable-threads
