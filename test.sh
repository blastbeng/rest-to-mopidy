#/bin/sh
curl -H 'Content-Type: application/json; charset=utf-8' -d '{"data":{"text": "ciao", "voice": "google"}}' http://192.168.1.90:5101/audio/play