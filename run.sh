#!/usr/bin/env bash
/usr/bin/mkdir -p ./config
/usr/bin/mkdir -p /run/user/1000/tmp/rest-to-tts
/usr/bin/rm -f /run/user/1000/tmp/rest-to-tts/fakeyou_voices.sqlite || true
cd /opt/rest-to-mopidy/
source .venv/bin/activate; uwsgi --ini ./uwsgi.ini --enable-threads


