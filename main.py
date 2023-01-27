import os
import logging
import utils
import audiodb
import requests
import json
import threading
import random
import sys
import shutil
from datetime import datetime
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask, request, send_file, Response, jsonify, render_template, make_response, after_this_request, g
from flask_restx import Api, Resource, reqparse
from flask_apscheduler import APScheduler
from pathlib import Path
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=int(os.environ.get("LOG_LEVEL")),
        datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger('werkzeug')
log.setLevel(int(os.environ.get("LOG_LEVEL")))

app = Flask(__name__)
class Config:    
    SCHEDULER_API_ENABLED = True

scheduler = APScheduler()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["20/minute"],
    storage_uri="memory://",
)

app.config.from_object(Config())
api = Api(app)


def get_response_str(text: str):
    r = Response(response=text, status=200, mimetype="text/xml")
    r.headers["Content-Type"] = "text/xml; charset=utf-8"
    return r

nsaudio = api.namespace('audio', 'TTS APIs')

@nsaudio.route('/generate/<string:text>/')
@nsaudio.route('/generate/<string:text>/<string:voice>/')
class AudioGenerateClass(Resource):
  def get (self, text: str, voice = "random"):
    try:
      tts_out, voice_to_use = utils.get_tts(text, voice=voice)
      if tts_out is not None:
        return send_file(tts_out, attachment_filename='audio.mp3', mimetype='audio/mpeg')
      else:
        return make_response("TTS Generation Error!", 500)
    except Exception as e:
      g.request_error = str(e)
      return make_response(g.get('request_error'), 500)

@nsaudio.route('/play')
class AudioPlayClass(Resource):
  def post (self):
    try:
      text = request.json.get("data").get("text")
      if text is None:
        return get_response_str("text is mandatory.")
      voice = request.json.get("data").get("voice")
      if voice is not None and utils.get_voice_name(voice) is None:
        return get_response_str("voice not found.")
      result = utils.play_tts(text, voice)
      if result is not None:
        return get_response_str(result)
      else:
        return make_response("TTS Generation Error!", 500)
    except Exception as e:
      g.request_error = str(e)
      return make_response(g.get('request_error'), 500)

nsdatabase = api.namespace('database', 'DATABASE APIs')

@nsdatabase.route('/delete/bytext/<string:text>/')
class UtilsDeleteByText(Resource):
  def get (self, text: str):
    return get_response_str(audiodb.delete_by_name(text))

nsutils = api.namespace('utils', 'UTILS APIs')


@nsutils.route('/get_configured_voices')
class GetConfiguredVoices(Resource):
  def get(self):
    return jsonify(utils.get_configured_voices())


@nsutils.route('/fakeyou/listvoices/')
@nsutils.route('/fakeyou/listvoices/<string:lang>')
class FakeYouListVoices(Resource):
  def get(self, lang = "it"):
    return jsonify(utils.list_fakeyou_voices(lang))

@limiter.limit("1/second")
@nsutils.route('/healthcheck')
class Healthcheck(Resource):
  def get (self):
    return "Ok!"

@nsutils.route('/reset')
class Reset(Resource):
  def get (self):
    try:
      result = utils.reset()
      if result is not None:
        return get_response_str(result)
      else:
        return make_response("Reset Error!", 500)
    except Exception as e:
      g.request_error = str(e)
      return make_response(g.get('request_error'), 500)
  
@scheduler.task('interval', id='login_fakeyou', hours=11, misfire_grace_time=900)
def login_fakeyou():
  utils.login_fakeyou()

audiodb.create_empty_tables()
limiter.init_app(app)
scheduler.init_app(app)
scheduler.start()
utils.login_fakeyou()

if __name__ == '__main__':
  app.run()
